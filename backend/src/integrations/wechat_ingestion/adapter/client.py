from __future__ import annotations

from sqlalchemy.orm import Session
from collections.abc import Callable

from src.core.config import Settings
from src.integrations.wechat_ingestion.pipeline.orchestrator import WechatIngestionPipeline
from src.models import ArticleSource


class WeChatIngestionAdapter:
    def __init__(self, settings: Settings):
        self.pipeline = WechatIngestionPipeline(settings)

    def ingest_source(
        self,
        db: Session,
        source: ArticleSource,
        page_start: int = 1,
        page_end: int = 20,
        since_days: int | None = None,
        progress_callback: Callable[[dict], None] | None = None,
    ):
        return self.pipeline.run(
            db,
            source,
            page_start=page_start,
            page_end=page_end,
            since_days=since_days,
            progress_callback=progress_callback,
        )
