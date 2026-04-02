from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.api.deps import db_session
from src.core.config import get_settings
from src.models import Article

router = APIRouter(prefix="/system", tags=["system"])


@router.get("/status")
def system_status() -> dict[str, object]:
    settings = get_settings()
    return {
        "app_name": settings.app_name,
        "environment": settings.environment,
        "database_url": settings.database_url,
        "redis_url": settings.redis_url,
        "llm_provider": settings.llm_provider,
        "auto_create_schema": settings.auto_create_schema,
    }


@router.get("/taxonomies/article-tags")
def article_tag_taxonomy(db: Session = Depends(db_session)) -> dict[str, list[str]]:
    tags: list[str] = []
    seen: set[str] = set()
    for row_tags in db.scalars(select(Article.topic_tags)).all():
        if not row_tags:
            continue
        for raw in row_tags:
            value = str(raw).strip()
            if not value:
                continue
            parts = [part.strip() for part in value.split("/") if part.strip()]
            current = ""
            for part in parts:
                current = part if not current else f"{current}/{part}"
                if current not in seen:
                    seen.add(current)
                    tags.append(current)
    tags.sort(key=lambda item: item.lower())
    return {
        "tags": tags,
    }
