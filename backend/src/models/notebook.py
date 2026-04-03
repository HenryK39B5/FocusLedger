from __future__ import annotations

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base, IDMixin, TimestampMixin


class Notebook(Base, IDMixin, TimestampMixin):
    __tablename__ = "notebooks"

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    emoji: Mapped[str] = mapped_column(String(16), nullable=False, default="📒")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    notebook_articles = relationship(
        "NotebookArticle",
        back_populates="notebook",
        cascade="all, delete-orphan",
        order_by="NotebookArticle.created_at.desc()",
    )
    chat_messages = relationship(
        "NotebookChatMessage",
        back_populates="notebook",
        cascade="all, delete-orphan",
        order_by="NotebookChatMessage.created_at.asc()",
    )
    podcast_scripts = relationship(
        "NotebookPodcastScript",
        back_populates="notebook",
        cascade="all, delete-orphan",
        order_by="NotebookPodcastScript.created_at.desc()",
    )
