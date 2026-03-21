from __future__ import annotations

from sqlalchemy.orm import Session

from src.core.config import Settings
from src.integrations.wechat_ingestion.adapter.client import WeChatIngestionAdapter
from src.models import ArticleSource
from src.schemas.dashboard import IngestionResult


class IngestionService:
    def run_source(
        self,
        db: Session,
        settings: Settings,
        source: ArticleSource,
        page_start: int = 1,
        page_end: int = 20,
        since_days: int | None = None,
    ) -> IngestionResult:
        adapter = WeChatIngestionAdapter(settings)
        outcome = adapter.ingest_source(
            db,
            source,
            page_start=page_start,
            page_end=page_end,
            since_days=since_days,
        )
        return IngestionResult(
            source_id=source.id,
            source_name=source.name,
            imported_count=outcome.imported_count,
            updated_count=outcome.updated_count,
            failed_count=outcome.failed_count,
            message=outcome.message,
            article_ids=outcome.article_ids,
        )
