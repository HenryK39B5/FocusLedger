from __future__ import annotations

from sqlalchemy import ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base, IDMixin, TimestampMixin


class SourceCredential(Base, IDMixin, TimestampMixin):
    __tablename__ = "source_credentials"

    source_id: Mapped[str] = mapped_column(ForeignKey("article_sources.id"), nullable=False, unique=True, index=True)
    provider: Mapped[str] = mapped_column(String(64), default="manual", nullable=False)
    raw_link: Mapped[str] = mapped_column(String(4096), nullable=False)
    token_biz: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    uin: Mapped[str] = mapped_column(String(255), nullable=False)
    key: Mapped[str] = mapped_column(String(2048), nullable=False)
    pass_ticket: Mapped[str] = mapped_column(String(4096), nullable=False)
    appmsg_token: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    session_us: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    scene: Mapped[str | None] = mapped_column(String(64), nullable=True)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    raw_query: Mapped[dict] = mapped_column(JSON, default=dict)

    source = relationship("ArticleSource", back_populates="credential", lazy="joined")
