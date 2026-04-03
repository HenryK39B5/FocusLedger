from __future__ import annotations

from sqlalchemy import ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base, IDMixin, TimestampMixin


class NotebookChatMessage(Base, IDMixin, TimestampMixin):
    __tablename__ = "notebook_chat_messages"

    notebook_id: Mapped[str] = mapped_column(ForeignKey("notebooks.id", ondelete="CASCADE"), index=True, nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    citations: Mapped[list[str]] = mapped_column(JSON, default=list)

    notebook = relationship("Notebook", back_populates="chat_messages")
