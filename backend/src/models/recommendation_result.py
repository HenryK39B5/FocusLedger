from __future__ import annotations

from sqlalchemy import Float, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base, IDMixin, TimestampMixin


class RecommendationResult(Base, IDMixin, TimestampMixin):
    __tablename__ = "recommendation_results"

    user_id: Mapped[str] = mapped_column(ForeignKey("user_profiles.id"), index=True)
    article_id: Mapped[str] = mapped_column(ForeignKey("articles.id"), index=True)
    ranking_score: Mapped[float] = mapped_column(Float, default=0.0)
    topic_match_score: Mapped[float] = mapped_column(Float, default=0.0)
    type_match_score: Mapped[float] = mapped_column(Float, default=0.0)
    style_match_score: Mapped[float] = mapped_column(Float, default=0.0)
    novelty_score: Mapped[float] = mapped_column(Float, default=0.0)
    freshness_score: Mapped[float] = mapped_column(Float, default=0.0)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)

