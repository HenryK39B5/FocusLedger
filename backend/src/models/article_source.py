from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base, IDMixin, TimestampMixin


class ArticleSource(Base, IDMixin, TimestampMixin):
    __tablename__ = "article_sources"

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    source_identifier: Mapped[str | None] = mapped_column(String(2048), nullable=True, unique=True)
    biz: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    public_home_link: Mapped[str] = mapped_column(String(2048), nullable=False)
    source_group: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    credential_status: Mapped[str] = mapped_column(String(32), default="unknown", nullable=False, index=True)
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_sync_succeeded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_sync_failed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_error_message: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    credential = relationship(
        "SourceCredential",
        back_populates="source",
        uselist=False,
        cascade="all, delete-orphan",
    )
    ingestion_jobs = relationship("IngestionJob", back_populates="source", cascade="all, delete-orphan")
