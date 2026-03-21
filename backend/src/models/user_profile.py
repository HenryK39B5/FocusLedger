from __future__ import annotations

from sqlalchemy import JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base, IDMixin, TimestampMixin


class UserProfile(Base, IDMixin, TimestampMixin):
    __tablename__ = "user_profiles"

    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    preferred_topics: Mapped[list[str]] = mapped_column(JSON, default=list)
    disliked_topics: Mapped[list[str]] = mapped_column(JSON, default=list)
    preferred_content_types: Mapped[list[str]] = mapped_column(JSON, default=list)
    preferred_styles: Mapped[list[str]] = mapped_column(JSON, default=list)
    followed_topics: Mapped[list[str]] = mapped_column(JSON, default=list)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

