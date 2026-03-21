from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session

from src.models import (
    Article,
    ArticleEmbedding,
    ArticleMetrics,
    ArticleSource,
    FeedbackEvent,
    NoveltyAnalysis,
    RecommendationResult,
)
from src.schemas.content import ArticleSummaryRead

SHANGHAI_TZ = ZoneInfo("Asia/Shanghai")


def parse_publish_datetime(value: str | None, created_at: datetime | None = None) -> datetime | None:
    if value:
        raw = value.strip()
        if raw:
            if raw.isdigit():
                timestamp = int(raw)
                if len(raw) >= 13:
                    timestamp = int(raw[:10])
                return datetime.fromtimestamp(timestamp, tz=timezone.utc)
            for candidate in (raw, raw.replace("Z", "+00:00")):
                try:
                    parsed = datetime.fromisoformat(candidate)
                    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
                except ValueError:
                    continue
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
                try:
                    return datetime.strptime(raw, fmt).replace(tzinfo=timezone.utc)
                except ValueError:
                    continue

    if created_at is None:
        return None
    return created_at if created_at.tzinfo else created_at.replace(tzinfo=timezone.utc)


def normalize_publish_time(value: str | None, created_at: datetime | None = None) -> str | None:
    parsed = parse_publish_datetime(value, created_at)
    if parsed is None:
        return value
    return parsed.astimezone(SHANGHAI_TZ).strftime("%Y-%m-%d %H:%M:%S")


def normalize_publish_date(value: str | None, created_at: datetime | None = None) -> str | None:
    parsed = parse_publish_datetime(value, created_at)
    if parsed is None:
        return None
    return parsed.astimezone(SHANGHAI_TZ).date().isoformat()


class ArticleService:
    def list_articles(
        self,
        db: Session,
        limit: int = 20,
        source_id: str | None = None,
        q: str | None = None,
        page: int = 1,
        page_size: int | None = None,
        sort: str = "latest",
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> tuple[list[Article], int]:
        stmt = select(Article).join(ArticleSource, Article.source_id == ArticleSource.id)
        if source_id:
            stmt = stmt.where(Article.source_id == source_id)
        if q:
            pattern = f"%{q.strip().lower()}%"
            stmt = stmt.where(
                or_(
                    func.lower(Article.title).like(pattern),
                    func.lower(func.coalesce(Article.summary, "")).like(pattern),
                    func.lower(func.coalesce(Article.raw_text, "")).like(pattern),
                    func.lower(ArticleSource.name).like(pattern),
                )
            )

        articles = list(db.scalars(stmt).all())

        filtered: list[Article] = []
        for article in articles:
            publish_date = normalize_publish_date(article.publish_time, article.created_at)
            if date_from and publish_date and publish_date < date_from:
                continue
            if date_from and not publish_date:
                continue
            if date_to and publish_date and publish_date > date_to:
                continue
            if date_to and not publish_date:
                continue
            filtered.append(article)

        reverse = sort != "oldest"
        filtered.sort(
            key=lambda article: parse_publish_datetime(article.publish_time, article.created_at) or article.created_at,
            reverse=reverse,
        )

        total = len(filtered)
        if page_size is not None:
            safe_page = max(page, 1)
            safe_page_size = max(page_size, 1)
            start = (safe_page - 1) * safe_page_size
            end = start + safe_page_size
            filtered = filtered[start:end]
        else:
            filtered = filtered[:limit]

        return filtered, total

    def get_article(self, db: Session, article_id: str) -> Article | None:
        article = db.get(Article, article_id)
        if article:
            article.publish_time = normalize_publish_time(article.publish_time, article.created_at)
        return article

    def get_recent_history(self, db: Session, source_id: str | None = None, limit: int = 10) -> list[Article]:
        stmt = select(Article).order_by(Article.created_at.desc()).limit(limit)
        if source_id:
            stmt = stmt.where(Article.source_id == source_id)
        rows = list(db.scalars(stmt).all())
        for article in rows:
            article.publish_time = normalize_publish_time(article.publish_time, article.created_at)
        return rows

    def to_summary_rows(self, articles: list[Article]) -> list[ArticleSummaryRead]:
        return [
            ArticleSummaryRead(
                id=article.id,
                source_id=article.source_id,
                title=article.title,
                source_name=article.source.name if article.source else "",
                publish_time=normalize_publish_time(article.publish_time, article.created_at),
                created_at=article.created_at,
                summary=article.summary,
                topic_tags=article.topic_tags,
                style_tags=article.style_tags,
                source_tags=article.source.tags if article.source else [],
                source_group=article.source.source_group if article.source else None,
            )
            for article in articles
        ]

    def delete_article(self, db: Session, article: Article) -> None:
        db.execute(delete(ArticleEmbedding).where(ArticleEmbedding.article_id == article.id))
        db.execute(delete(ArticleMetrics).where(ArticleMetrics.article_id == article.id))
        db.execute(delete(NoveltyAnalysis).where(NoveltyAnalysis.article_id == article.id))
        db.execute(delete(RecommendationResult).where(RecommendationResult.article_id == article.id))
        db.execute(delete(FeedbackEvent).where(FeedbackEvent.article_id == article.id))
        db.delete(article)
        db.flush()

    def batch_delete_articles(self, db: Session, article_ids: list[str]) -> list[str]:
        cleaned_ids = [article_id.strip() for article_id in article_ids if article_id and article_id.strip()]
        if not cleaned_ids:
            return []
        articles = list(db.scalars(select(Article).where(Article.id.in_(cleaned_ids))).all())
        deleted_ids: list[str] = []
        for article in articles:
            deleted_ids.append(article.id)
            self.delete_article(db, article)
        return deleted_ids
