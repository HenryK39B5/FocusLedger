from __future__ import annotations

from sqlalchemy.orm import Session

from src.core.config import get_settings
from src.db.session import SessionLocal
from src.integrations.wechat_ingestion.adapter.client import WeChatIngestionAdapter
from src.models import ArticleSource
from src.tasks.celery_app import celery_app


@celery_app.task(name="focusledger.ingest_source")
def ingest_source_task(source_id: str, page_start: int = 1, page_end: int = 1) -> dict:
    settings = get_settings()
    db: Session = SessionLocal()
    try:
        source = db.get(ArticleSource, source_id)
        if not source:
            return {"ok": False, "message": "source not found"}
        adapter = WeChatIngestionAdapter(settings)
        outcome = adapter.ingest_source(db, source, page_start=page_start, page_end=page_end)
        db.commit()
        return {
            "ok": True,
            "imported_count": outcome.imported_count,
            "updated_count": outcome.updated_count,
            "failed_count": outcome.failed_count,
            "article_ids": outcome.article_ids,
        }
    finally:
        db.close()

