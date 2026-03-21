from __future__ import annotations

from datetime import datetime

from pydantic import Field

from src.schemas.common import SchemaBase


class DailyReportSectionRead(SchemaBase):
    title: str
    summary: str | None = None
    bullets: list[str] = Field(default_factory=list)
    article_ids: list[str] = Field(default_factory=list)


class DailyReportArticleRead(SchemaBase):
    id: str
    title: str
    source_name: str
    source_group: str | None = None
    source_tags: list[str] = Field(default_factory=list)
    publish_time: str | None = None
    summary: str | None = None
    topic_tags: list[str] = Field(default_factory=list)
    entity_tags: list[str] = Field(default_factory=list)
    style_tags: list[str] = Field(default_factory=list)
    content_type: str | None = None
    importance_score: float = 0.0


class DailyReportRead(SchemaBase):
    date: str
    title: str
    overview: str | None = None
    report_markdown: str
    follow_ups: list[str] = Field(default_factory=list)
    sections: list[DailyReportSectionRead] = Field(default_factory=list)
    articles: list[DailyReportArticleRead] = Field(default_factory=list)
    stats: dict[str, object] = Field(default_factory=dict)
    generated_at: datetime
    source_id: str | None = None
    source_group: str | None = None
