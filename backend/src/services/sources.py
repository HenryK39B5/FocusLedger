from __future__ import annotations

import re

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from src.models import Article, ArticleEmbedding, ArticleMetrics, ArticleSource, FeedbackEvent, NoveltyAnalysis, RecommendationResult
from src.schemas.content import ArticleSourceCreate, ArticleSourceDeleteRead, ArticleSourceUpdate


def _normalize_tags(tags: list[str] | None) -> list[str]:
    if not tags:
        return []
    normalized: list[str] = []
    seen: set[str] = set()
    for tag in tags:
        cleaned = tag.strip()
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        normalized.append(cleaned)
    return normalized


def normalize_group_path(value: str | None) -> str | None:
    if not value:
        return None
    parts = [part.strip() for part in re.split(r"[\\/]+", value) if part.strip()]
    if not parts:
        return None
    return "/".join(parts)


class SourceService:
    def list_sources(self, db: Session) -> list[ArticleSource]:
        return list(
            db.scalars(
                select(ArticleSource).order_by(ArticleSource.source_group.asc().nullsfirst(), ArticleSource.name.asc())
            ).all()
        )

    def get_source(self, db: Session, source_id: str) -> ArticleSource | None:
        return db.get(ArticleSource, source_id)

    def create_source(self, db: Session, payload: ArticleSourceCreate) -> ArticleSource:
        data = payload.model_dump()
        data["source_group"] = normalize_group_path(data.get("source_group"))
        data["tags"] = _normalize_tags(data.get("tags"))
        source = ArticleSource(**data)
        db.add(source)
        db.flush()
        return source

    def update_source(self, db: Session, source: ArticleSource, payload: ArticleSourceUpdate) -> ArticleSource:
        updates = payload.model_dump(exclude_unset=True)
        if "source_group" in updates:
            updates["source_group"] = normalize_group_path(updates["source_group"])
        if "tags" in updates:
            updates["tags"] = _normalize_tags(updates["tags"])
        for key, value in updates.items():
            setattr(source, key, value)
        db.flush()
        return source

    def delete_source(self, db: Session, source: ArticleSource) -> ArticleSourceDeleteRead:
        articles = list(db.scalars(select(Article).where(Article.source_id == source.id)).all())
        article_ids = [article.id for article in articles]
        if article_ids:
            db.execute(delete(ArticleEmbedding).where(ArticleEmbedding.article_id.in_(article_ids)))
            db.execute(delete(ArticleMetrics).where(ArticleMetrics.article_id.in_(article_ids)))
            db.execute(delete(NoveltyAnalysis).where(NoveltyAnalysis.article_id.in_(article_ids)))
            db.execute(delete(RecommendationResult).where(RecommendationResult.article_id.in_(article_ids)))
            db.execute(delete(FeedbackEvent).where(FeedbackEvent.article_id.in_(article_ids)))
            for article in articles:
                db.delete(article)
        deleted_count = len(article_ids)
        source_name = source.name
        db.delete(source)
        db.flush()
        return ArticleSourceDeleteRead(
            source_id=source.id,
            source_name=source_name,
            deleted_article_count=deleted_count,
        )
