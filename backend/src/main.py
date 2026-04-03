from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import (
    articles_router,
    health_router,
    ingestion_jobs_router,
    ingestions_router,
    notebooks_router,
    sources_router,
    status_router,
    wechat_router,
)
from src.core.config import get_settings
from src.core.logging import configure_logging
from src.db.base import Base
from src.db.session import engine
from src.models import *  # noqa: F403
from src.services.ingestion_jobs import ingestion_job_service


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging()
    app = FastAPI(title=settings.app_name, version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health_router, prefix=settings.api_prefix)
    app.include_router(sources_router, prefix=settings.api_prefix)
    app.include_router(articles_router, prefix=settings.api_prefix)
    app.include_router(notebooks_router, prefix=settings.api_prefix)
    app.include_router(ingestion_jobs_router, prefix=settings.api_prefix)
    app.include_router(ingestions_router, prefix=settings.api_prefix)
    app.include_router(status_router, prefix=settings.api_prefix)
    app.include_router(wechat_router, prefix=settings.api_prefix)

    @app.on_event("startup")
    def on_startup() -> None:
        if settings.auto_create_schema:
            Base.metadata.create_all(bind=engine)
        ingestion_job_service.reconcile_stale_runtime_state()

    @app.get("/")
    def root() -> dict[str, str]:
        return {"name": settings.app_name, "status": "ready"}

    return app


app = create_app()
