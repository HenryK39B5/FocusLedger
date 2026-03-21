from __future__ import annotations

from celery import Celery

from src.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "focusledger",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)
celery_app.conf.task_track_started = True

