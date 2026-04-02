from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base, IDMixin, TimestampMixin


class Article(Base, IDMixin, TimestampMixin):
    __tablename__ = "articles"

    source_id: Mapped[str] = mapped_column(ForeignKey("article_sources.id"), index=True)
    title: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    author: Mapped[str | None] = mapped_column(String(255), nullable=True)
    publish_time: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    url: Mapped[str] = mapped_column(String(2048), nullable=False, unique=True)
    raw_html_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    topic_tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    entity_tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    content_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    core_claims: Mapped[list[str]] = mapped_column(JSON, default=list)
    key_variables: Mapped[list[str]] = mapped_column(JSON, default=list)
    catalysts: Mapped[list[str]] = mapped_column(JSON, default=list)
    risks: Mapped[list[str]] = mapped_column(JSON, default=list)
    style_tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    recommendation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    is_favorited: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    llm_summary_status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False, index=True)
    llm_summary_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    llm_summary_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    source = relationship("ArticleSource", lazy="joined")
    metrics = relationship("ArticleMetrics", back_populates="article", cascade="all, delete-orphan")
    embeddings = relationship("ArticleEmbedding", back_populates="article", cascade="all, delete-orphan")

    @property
    def tags(self) -> list[str]:
        return list(self.topic_tags or [])

    @property
    def all_tags(self) -> list[str]:
        merged: list[str] = []
        for tag in [*(self.topic_tags or []), *((self.source.tags if self.source else []) or [])]:
            value = str(tag).strip()
            if value and value not in merged:
                merged.append(value)
        return merged
