from __future__ import annotations

from pydantic import Field

from src.schemas.common import SchemaBase


class IngestionResult(SchemaBase):
    source_id: str
    source_name: str
    imported_count: int = 0
    updated_count: int = 0
    failed_count: int = 0
    message: str = ""
    article_ids: list[str] = Field(default_factory=list)
    needs_refresh: bool = False
    credential_status_after_run: str = "unknown"
    failure_reason_category: str | None = None


class IngestionJobCreate(SchemaBase):
    source_id: str
    page_start: int = 1
    page_end: int = 20
    since_days: int | None = None
    date_from: str | None = None
    date_to: str | None = None


class IngestionJobRead(SchemaBase):
    id: str
    source_id: str
    source_name: str
    status: str
    page_start: int
    page_end: int
    since_days: int | None = None
    date_from: str | None = None
    date_to: str | None = None
    current_stage: str | None = None
    current_article_title: str | None = None
    current_article_url: str | None = None
    processed_count: int = 0
    imported_count: int = 0
    updated_count: int = 0
    failed_count: int = 0
    total_candidates: int | None = None
    message: str | None = None
    failure_reason_category: str | None = None
    started_at: str | None = None
    finished_at: str | None = None
    created_at: str
    updated_at: str


class IngestionJobListRead(SchemaBase):
    items: list[IngestionJobRead] = Field(default_factory=list)
