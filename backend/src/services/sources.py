from __future__ import annotations

import re

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from src.core.config import Settings
from src.integrations.wechat_ingestion.utils.discovery import build_public_home_link
from src.llm.providers import build_provider
from src.models import (
    Article,
    ArticleEmbedding,
    ArticleMetrics,
    ArticleSource,
    FeedbackEvent,
    IngestionJob,
    NoveltyAnalysis,
    RecommendationResult,
)
from src.schemas.content import (
    ArticleSourceCreate,
    ArticleSourceDeleteRead,
    SourceBatchAnalyzeRead,
    ArticleSourceUpdate,
    SourceCredentialCheckRead,
    SourceCredentialUpdate,
)
from src.services.source_credentials import SourceCredentialService


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

    def get_source_by_biz(self, db: Session, biz: str) -> ArticleSource | None:
        return db.scalar(select(ArticleSource).where(ArticleSource.biz == biz))

    def create_source(self, db: Session, settings: Settings, payload: ArticleSourceCreate) -> ArticleSource:
        existing = self.get_source_by_biz(db, payload.biz)
        if existing:
            raise ValueError("该公众号来源已经存在，请直接更新来源凭据。")

        data = payload.model_dump()
        biz = data["biz"].strip()
        source = ArticleSource(
            name=data["name"].strip(),
            source_type=data.get("source_type", "wechat_public_account"),
            biz=biz,
            public_home_link=(data.get("public_home_link") or build_public_home_link(biz)).strip(),
            source_group=normalize_group_path(data.get("source_group")),
            tags=_normalize_tags(data.get("tags")),
            description=(data.get("description") or "").strip() or None,
            enabled=bool(data.get("enabled", True)),
            credential_status="missing" if not (data.get("credential_link") or "").strip() else "unknown",
            source_identifier=None,
        )
        db.add(source)
        db.flush()

        credential_link = (data.get("credential_link") or "").strip()
        if credential_link:
            SourceCredentialService(settings).upsert_manual_credential(
                db,
                source,
                credential_link,
                validate_after_update=False,
            )
            db.flush()
        return source

    def update_source(self, db: Session, source: ArticleSource, payload: ArticleSourceUpdate) -> ArticleSource:
        updates = payload.model_dump(exclude_unset=True)
        if "source_group" in updates:
            updates["source_group"] = normalize_group_path(updates["source_group"])
        if "tags" in updates:
            updates["tags"] = _normalize_tags(updates["tags"])
        if "name" in updates and updates["name"] is not None:
            updates["name"] = updates["name"].strip()
        if "description" in updates and updates["description"] is not None:
            updates["description"] = updates["description"].strip() or None
        for key, value in updates.items():
            setattr(source, key, value)
        db.flush()
        return source

    def analyze_source(self, db: Session, settings: Settings, source: ArticleSource) -> ArticleSource:
        provider = build_provider(settings)
        article_titles = list(
            db.scalars(
                select(Article.title)
                .where(Article.source_id == source.id)
                .order_by(Article.publish_time.desc().nullslast(), Article.created_at.desc())
                .limit(20)
            ).all()
        )
        result = provider.classify_source(source.name, article_titles)
        source.source_group = normalize_group_path(str(result.get("source_group") or "").strip())
        source.tags = _normalize_tags(result.get("tags") or [])
        db.flush()
        return source

    def batch_analyze_sources(self, db: Session, settings: Settings, source_ids: list[str]) -> SourceBatchAnalyzeRead:
        cleaned_ids = [source_id.strip() for source_id in source_ids if source_id and source_id.strip()]
        if not cleaned_ids:
            return SourceBatchAnalyzeRead(analyzed_count=0, analyzed_ids=[], failed_ids=[])
        sources = list(db.scalars(select(ArticleSource).where(ArticleSource.id.in_(cleaned_ids))).all())
        analyzed_ids: list[str] = []
        failed_ids: list[str] = []
        for source in sources:
            try:
                self.analyze_source(db, settings, source)
                analyzed_ids.append(source.id)
            except Exception:
                failed_ids.append(source.id)
        return SourceBatchAnalyzeRead(
            analyzed_count=len(analyzed_ids),
            analyzed_ids=analyzed_ids,
            failed_ids=failed_ids,
        )

    def update_source_credential(
        self,
        db: Session,
        settings: Settings,
        source: ArticleSource,
        payload: SourceCredentialUpdate,
    ) -> tuple[ArticleSource, SourceCredentialCheckRead | None]:
        _, check = SourceCredentialService(settings).upsert_manual_credential(
            db,
            source,
            payload.raw_link,
            validate_after_update=payload.validate_after_update,
        )
        db.flush()
        return source, check

    def verify_source_credential(
        self,
        db: Session,
        settings: Settings,
        source: ArticleSource,
    ) -> SourceCredentialCheckRead:
        return SourceCredentialService(settings).verify_credential(db, source)

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

        db.execute(delete(IngestionJob).where(IngestionJob.source_id == source.id))
        deleted_count = len(article_ids)
        source_name = source.name
        db.delete(source)
        db.flush()
        return ArticleSourceDeleteRead(
            source_id=source.id,
            source_name=source_name,
            deleted_article_count=deleted_count,
        )
