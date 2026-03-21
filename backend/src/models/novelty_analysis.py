from __future__ import annotations

from sqlalchemy import Float, ForeignKey, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base, IDMixin, TimestampMixin


class NoveltyAnalysis(Base, IDMixin, TimestampMixin):
    __tablename__ = "novelty_analyses"

    article_id: Mapped[str] = mapped_column(ForeignKey("articles.id"), index=True)
    compared_article_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    repeated_points: Mapped[list[str]] = mapped_column(JSON, default=list)
    incremental_points: Mapped[list[str]] = mapped_column(JSON, default=list)
    novelty_type_breakdown: Mapped[dict] = mapped_column(JSON, default=dict)
    novelty_score: Mapped[float] = mapped_column(Float, default=0.0)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)

