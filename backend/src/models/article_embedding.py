from __future__ import annotations

from sqlalchemy import ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base, IDMixin, TimestampMixin


class ArticleEmbedding(Base, IDMixin, TimestampMixin):
    __tablename__ = "article_embeddings"

    article_id: Mapped[str] = mapped_column(
        ForeignKey("articles.id"), index=True, unique=True, nullable=False
    )
    embedding_model: Mapped[str] = mapped_column(String(128), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    embedding: Mapped[list[float]] = mapped_column(JSON, nullable=False)

    article = relationship("Article", back_populates="embeddings")
