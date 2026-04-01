from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from threading import Lock
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.core.config import Settings
from src.db.session import SessionLocal
from src.integrations.wechat_ingestion.adapter.client import WeChatIngestionAdapter
from src.models import ArticleSource, IngestionJob
from src.schemas.dashboard import IngestionJobCreate, IngestionJobListRead, IngestionJobRead
from src.services.source_credentials import SourceCredentialService

logger = logging.getLogger(__name__)


def _format_dt(value: datetime | None) -> str | None:
    if value is None:
        return None
    aware = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    return aware.astimezone(timezone.utc).isoformat()


class IngestionJobService:
    def __init__(self) -> None:
        self.executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="focusledger-ingestion")
        self._lock = Lock()

    def list_jobs(self, db: Session, source_id: str | None = None, limit: int = 50) -> IngestionJobListRead:
        stmt = select(IngestionJob).order_by(IngestionJob.created_at.desc()).limit(limit)
        if source_id:
            stmt = stmt.where(IngestionJob.source_id == source_id)
        jobs = list(db.scalars(stmt).all())
        return IngestionJobListRead(items=[self._to_read(job) for job in jobs])

    def get_job(self, db: Session, job_id: str) -> IngestionJob | None:
        return db.get(IngestionJob, job_id)

    def create_job(self, db: Session, settings: Settings, payload: IngestionJobCreate) -> IngestionJob:
        source = db.get(ArticleSource, payload.source_id)
        if not source:
            raise ValueError("source not found")

        existing = db.scalar(
            select(IngestionJob).where(
                IngestionJob.source_id == payload.source_id,
                IngestionJob.status.in_(("pending", "running")),
            )
        )
        if existing:
            raise ValueError("该来源已有进行中的同步任务，请等待当前任务结束。")

        job = IngestionJob(
            source_id=payload.source_id,
            status="pending",
            page_start=payload.page_start,
            page_end=payload.page_end,
            since_days=payload.since_days,
            current_stage="verifying_credential",
            message="任务已创建，等待执行。",
        )
        db.add(job)
        db.flush()
        return job

    def reconcile_stale_runtime_state(self) -> None:
        now = datetime.now(timezone.utc)
        db = SessionLocal()
        try:
            stale_jobs = list(
                db.scalars(select(IngestionJob).where(IngestionJob.status.in_(("pending", "running")))).all()
            )
            for job in stale_jobs:
                job.status = "failed"
                job.finished_at = now
                job.failure_reason_category = job.failure_reason_category or "interrupted"
                job.message = "服务重启，之前的同步任务已中断，请重新发起同步。"

            if stale_jobs:
                logger.info("reconciled %s stale ingestion jobs on startup", len(stale_jobs))
                db.commit()
        finally:
            db.close()

    def start_job(self, settings: Settings, job_id: str) -> None:
        with self._lock:
            self.executor.submit(self._run_job, settings, job_id)

    def _persist_job_update(self, job_id: str, **fields: Any) -> None:
        progress_db = SessionLocal()
        try:
            job = progress_db.get(IngestionJob, job_id)
            if not job:
                return
            for key, value in fields.items():
                setattr(job, key, value)
            progress_db.commit()
        finally:
            progress_db.close()

    def _run_job(self, settings: Settings, job_id: str) -> None:
        db = SessionLocal()
        try:
            job = db.get(IngestionJob, job_id)
            if not job:
                return

            source = db.get(ArticleSource, job.source_id)
            if not source:
                self._persist_job_update(
                    job_id,
                    status="failed",
                    message="来源不存在，无法执行同步。",
                    finished_at=datetime.now(timezone.utc),
                )
                return

            self._persist_job_update(
                job_id,
                status="running",
                started_at=datetime.now(timezone.utc),
                current_stage="verifying_credential",
                message="开始验证来源凭据。",
            )

            credential_service = SourceCredentialService(settings)
            check = credential_service.verify_credential(db, source)
            db.commit()
            db.refresh(source)

            if not check.valid:
                credential_service.record_sync_result(
                    db,
                    source,
                    success=False,
                    failure_reason_category=check.error_code,
                    error_message=check.message,
                )
                db.commit()
                self._persist_job_update(
                    job_id,
                    status="failed",
                    current_stage="verifying_credential",
                    message=check.message,
                    failure_reason_category=check.error_code,
                    finished_at=datetime.now(timezone.utc),
                )
                return

            adapter = WeChatIngestionAdapter(settings)

            def progress_callback(event: dict[str, Any]) -> None:
                fields: dict[str, Any] = {}
                if "stage" in event:
                    fields["current_stage"] = event["stage"]
                if "article_title" in event:
                    fields["current_article_title"] = event["article_title"]
                if "article_url" in event:
                    fields["current_article_url"] = event["article_url"]
                if "processed_count" in event and event["processed_count"] is not None:
                    fields["processed_count"] = int(event["processed_count"])
                if "imported_count" in event and event["imported_count"] is not None:
                    fields["imported_count"] = int(event["imported_count"])
                if "updated_count" in event and event["updated_count"] is not None:
                    fields["updated_count"] = int(event["updated_count"])
                if "failed_count" in event and event["failed_count"] is not None:
                    fields["failed_count"] = int(event["failed_count"])
                if "total_candidates" in event and event["total_candidates"] is not None:
                    fields["total_candidates"] = int(event["total_candidates"])
                if "message" in event:
                    fields["message"] = event["message"]
                if fields:
                    self._persist_job_update(job_id, **fields)

            outcome = adapter.ingest_source(
                db,
                source,
                page_start=job.page_start,
                page_end=job.page_end,
                since_days=job.since_days,
                progress_callback=progress_callback,
            )
            credential_service.record_sync_result(
                db,
                source,
                success=outcome.failed_count == 0 and outcome.failure_reason_category != "no_articles_in_range",
                failure_reason_category=outcome.failure_reason_category,
                error_message=outcome.message,
            )
            db.commit()
            self._persist_job_update(
                job_id,
                status="succeeded" if outcome.failed_count == 0 else "failed",
                current_stage="finalizing",
                processed_count=outcome.imported_count + outcome.updated_count + outcome.failed_count,
                imported_count=outcome.imported_count,
                updated_count=outcome.updated_count,
                failed_count=outcome.failed_count,
                total_candidates=outcome.total_candidates,
                message=outcome.message,
                failure_reason_category=outcome.failure_reason_category,
                finished_at=datetime.now(timezone.utc),
            )
        except Exception as exc:  # pragma: no cover
            logger.exception("Ingestion job %s failed", job_id)
            db.rollback()
            self._persist_job_update(
                job_id,
                status="failed",
                message=str(exc),
                failure_reason_category="internal_error",
                finished_at=datetime.now(timezone.utc),
            )
        finally:
            db.close()

    def _to_read(self, job: IngestionJob) -> IngestionJobRead:
        return IngestionJobRead(
            id=job.id,
            source_id=job.source_id,
            source_name=job.source.name if job.source else "",
            status=job.status,
            page_start=job.page_start,
            page_end=job.page_end,
            since_days=job.since_days,
            current_stage=job.current_stage,
            current_article_title=job.current_article_title,
            current_article_url=job.current_article_url,
            processed_count=job.processed_count,
            imported_count=job.imported_count,
            updated_count=job.updated_count,
            failed_count=job.failed_count,
            total_candidates=job.total_candidates,
            message=job.message,
            failure_reason_category=job.failure_reason_category,
            started_at=_format_dt(job.started_at),
            finished_at=_format_dt(job.finished_at),
            created_at=_format_dt(job.created_at) or "",
            updated_at=_format_dt(job.updated_at) or "",
        )

    def get_job_read(self, db: Session, job_id: str) -> IngestionJobRead | None:
        job = self.get_job(db, job_id)
        if not job:
            return None
        return self._to_read(job)


ingestion_job_service = IngestionJobService()
