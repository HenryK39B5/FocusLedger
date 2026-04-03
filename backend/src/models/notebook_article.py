from __future__ import annotations

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base, IDMixin, TimestampMixin


class NotebookArticle(Base, IDMixin, TimestampMixin):
    __tablename__ = "notebook_articles"
    __table_args__ = (UniqueConstraint("notebook_id", "article_id", name="uq_notebook_article_pair"),)

    notebook_id: Mapped[str] = mapped_column(ForeignKey("notebooks.id", ondelete="CASCADE"), index=True, nullable=False)
    article_id: Mapped[str] = mapped_column(ForeignKey("articles.id", ondelete="CASCADE"), index=True, nullable=False)

    notebook = relationship("Notebook", back_populates="notebook_articles")
    article = relationship("Article", lazy="joined", back_populates="notebook_links")
