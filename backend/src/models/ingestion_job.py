from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base, IDMixin, TimestampMixin


class IngestionJob(Base, IDMixin, TimestampMixin):
    __tablename__ = "ingestion_jobs"

    source_id: Mapped[str] = mapped_column(ForeignKey("article_sources.id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", index=True)
    page_start: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    page_end: Mapped[int] = mapped_column(Integer, nullable=False, default=20)
    since_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    date_from: Mapped[str | None] = mapped_column(String(10), nullable=True)
    date_to: Mapped[str | None] = mapped_column(String(10), nullable=True)
    current_stage: Mapped[str | None] = mapped_column(String(64), nullable=True)
    current_article_title: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    current_article_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    processed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    imported_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_candidates: Mapped[int | None] = mapped_column(Integer, nullable=True)
    message: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    failure_reason_category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    source = relationship("ArticleSource", back_populates="ingestion_jobs", lazy="joined")
