from __future__ import annotations

from pydantic import Field

from src.schemas.common import SchemaBase


class QClawDailyReportArticleLinkRead(SchemaBase):
    id: str
    title: str
    url: str
    source_name: str


class QClawDailyReportRead(SchemaBase):
    ok: bool = True
    date: str
    title: str
    reply_text: str
    report_markdown: str | None = None
    overview: str | None = None
    matched_articles: int = 0
    selected_articles: int = 0
    source_group: str | None = None
    source_id: str | None = None
    article_links: list[QClawDailyReportArticleLinkRead] = Field(default_factory=list)
