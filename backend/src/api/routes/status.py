from __future__ import annotations

from fastapi import APIRouter

from src.core.config import get_settings

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

