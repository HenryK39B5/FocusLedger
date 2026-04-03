from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session

from src.core.config import Settings
from src.llm.providers import build_provider
from src.llm.taxonomy_files import load_article_tag_taxonomy
from src.models import (
    Article,
    ArticleEmbedding,
    ArticleMetrics,
    ArticleSource,
    FeedbackEvent,
    NoveltyAnalysis,
    RecommendationResult,
)
from src.schemas.content import ArticleSummaryRead, ArticleUpdate

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
    def _query_filtered_articles(
        self,
        db: Session,
        *,
        source_id: str | None = None,
        q: str | None = None,
        sort: str = "latest",
        date_from: str | None = None,
        date_to: str | None = None,
        llm_status: str | None = None,
        favorited_only: bool = False,
        tags: list[str] | None = None,
    ) -> list[Article]:
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
        normalized_filter_tags = self._normalized_tags(tags)
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
            if llm_status and article.llm_summary_status != llm_status:
                continue
            if favorited_only and not article.is_favorited:
                continue
            if normalized_filter_tags:
                article_tags = self._normalized_tags(article.tags)
                if not all(self._tag_matches(article_tags, tag) for tag in normalized_filter_tags):
                    continue
            filtered.append(article)

        reverse = sort != "oldest"
        filtered.sort(
            key=lambda article: parse_publish_datetime(article.publish_time, article.created_at) or article.created_at,
            reverse=reverse,
        )
        return filtered

    def _tag_matches(self, article_tags: list[str], selected_tag: str) -> bool:
        cleaned_selected = str(selected_tag).strip()
        if not cleaned_selected:
            return False
        for raw_tag in self._normalized_tags(article_tags):
            if raw_tag == cleaned_selected or raw_tag.startswith(f"{cleaned_selected}/"):
                return True
        return False

    def _normalized_tags(self, tags: list[str] | None) -> list[str]:
        if not tags:
            return []
        items: list[str] = []
        for raw in tags:
            value = str(raw).strip()
            if value and value not in items:
                items.append(value)
        return items

    def _normalized_content_type(self, value: str | None) -> str | None:
        cleaned = (value or "").strip()
        return cleaned or None

    def _set_llm_state(
        self,
        article: Article,
        *,
        status: str,
        error: str | None = None,
        updated_at: datetime | None = None,
    ) -> None:
        article.llm_summary_status = status
        article.llm_summary_error = error
        if updated_at is not None:
            article.llm_summary_updated_at = updated_at.astimezone(timezone.utc)

    def _set_favorite(self, article: Article, favorited: bool) -> None:
        article.is_favorited = favorited

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
        llm_status: str | None = None,
        favorited_only: bool = False,
        tags: list[str] | None = None,
    ) -> tuple[list[Article], int]:
        filtered = self._query_filtered_articles(
            db,
            source_id=source_id,
            q=q,
            sort=sort,
            date_from=date_from,
            date_to=date_to,
            llm_status=llm_status,
            favorited_only=favorited_only,
            tags=tags,
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
                tags=article.tags,
                all_tags=article.all_tags,
                topic_tags=article.topic_tags,
                style_tags=article.style_tags,
                source_tags=article.source.tags if article.source else [],
                source_group=article.source.source_group if article.source else None,
                content_type=article.content_type,
                is_favorited=article.is_favorited,
                llm_summary_status=article.llm_summary_status,
            )
            for article in articles
        ]

    def update_article(self, db: Session, article: Article, payload: ArticleUpdate) -> Article:
        updates = payload.model_dump(exclude_unset=True)
        if "tags" in updates and updates["tags"] is not None:
            normalized_tags = self._normalized_tags(updates["tags"])
            article.topic_tags = normalized_tags
        if "is_favorited" in updates and updates["is_favorited"] is not None:
            self._set_favorite(article, bool(updates["is_favorited"]))
        db.flush()
        return article

    def analyze_article(self, db: Session, settings: Settings, article: Article) -> Article:
        text = (article.raw_text or "").strip()
        if not text:
            raise ValueError("article has no raw text")

        provider = build_provider(settings)
        if provider.name == "rule":
            raise ValueError("LLM provider unavailable; please configure a real LLM API first")
        now = datetime.now(timezone.utc)
        allowed_tags = set(load_article_tag_taxonomy())

        self._set_llm_state(article, status="processing", error=None)
        db.flush()

        try:
            features = provider.extract_features(text)
            summary = str(features.get("summary") or "").strip()
            tags = self._normalized_tags(features.get("topic_tags") or [])

            if allowed_tags:
                tags = [item for item in tags if item in allowed_tags]

            article.summary = summary or None
            article.topic_tags = tags
            self._set_llm_state(article, status="completed", error=None, updated_at=now)
            db.flush()
            return article
        except Exception as exc:
            self._set_llm_state(article, status="failed", error=str(exc), updated_at=now)
            db.flush()
            raise

    def batch_analyze_articles(self, db: Session, settings: Settings, article_ids: list[str]) -> tuple[list[str], list[str]]:
        cleaned_ids = [article_id.strip() for article_id in article_ids if article_id and article_id.strip()]
        if not cleaned_ids:
            return [], []

        articles = list(db.scalars(select(Article).where(Article.id.in_(cleaned_ids))).all())
        analyzed_ids: list[str] = []
        failed_ids: list[str] = []
        for article in articles:
            try:
                self.analyze_article(db, settings, article)
                analyzed_ids.append(article.id)
            except Exception:
                failed_ids.append(article.id)
        return analyzed_ids, failed_ids

    def batch_analyze_articles_by_query(
        self,
        db: Session,
        settings: Settings,
        *,
        source_id: str | None = None,
        q: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        favorited_only: bool = False,
        tags: list[str] | None = None,
        max_items: int = 100,
        target: str = "pending",
    ) -> tuple[list[str], list[str]]:
        candidates = self._query_filtered_articles(
            db,
            source_id=source_id,
            q=q,
            sort="latest",
            date_from=date_from,
            date_to=date_to,
            favorited_only=favorited_only,
            tags=tags,
        )
        if target == "pending":
            candidates = [article for article in candidates if article.llm_summary_status == "pending"]
        elif target == "retryable":
            candidates = [article for article in candidates if article.llm_summary_status in {"pending", "failed"}]
        elif target == "all":
            candidates = list(candidates)
        else:
            raise ValueError("invalid batch analyze target")

        candidates = candidates[: max(max_items, 1)]

        analyzed_ids: list[str] = []
        failed_ids: list[str] = []
        for article in candidates:
            try:
                self.analyze_article(db, settings, article)
                analyzed_ids.append(article.id)
            except Exception:
                failed_ids.append(article.id)
        return analyzed_ids, failed_ids

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
