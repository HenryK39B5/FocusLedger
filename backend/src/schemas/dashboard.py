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
