from __future__ import annotations

from sqlalchemy import Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base, IDMixin, TimestampMixin


class FeedbackEvent(Base, IDMixin, TimestampMixin):
    __tablename__ = "feedback_events"

    user_id: Mapped[str] = mapped_column(ForeignKey("user_profiles.id"), index=True)
    article_id: Mapped[str] = mapped_column(ForeignKey("articles.id"), index=True)
    feedback_type: Mapped[str] = mapped_column(String(64), nullable=False)
    feedback_value: Mapped[float] = mapped_column(Float, default=1.0)

