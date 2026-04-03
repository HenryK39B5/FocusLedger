from __future__ import annotations

from sqlalchemy import ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base, IDMixin, TimestampMixin


class NotebookPodcastScript(Base, IDMixin, TimestampMixin):
    __tablename__ = "notebook_podcast_scripts"

    notebook_id: Mapped[str] = mapped_column(ForeignKey("notebooks.id", ondelete="CASCADE"), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    format: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    target_minutes: Mapped[int] = mapped_column(nullable=False, default=5)
    focus_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="completed", index=True)
    audio_status: Mapped[str] = mapped_column(String(32), nullable=False, default="not_ready", index=True)
    audio_job_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    audio_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    audio_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    generation_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    cited_article_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    script_markdown: Mapped[str] = mapped_column(Text, nullable=False)
    script_json: Mapped[dict] = mapped_column(JSON, default=dict)

    notebook = relationship("Notebook", back_populates="podcast_scripts")
