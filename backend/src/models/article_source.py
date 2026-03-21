from __future__ import annotations

from sqlalchemy import Boolean, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base, IDMixin, TimestampMixin


class ArticleSource(Base, IDMixin, TimestampMixin):
    __tablename__ = "article_sources"

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    source_identifier: Mapped[str] = mapped_column(String(2048), nullable=False, unique=True)
    source_group: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
