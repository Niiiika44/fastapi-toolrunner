from celery import Celery

import app.core.celery_signals  # noqa: F401
from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND_URL
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    worker_prefetch_multiplier=1,
    timezone="UTC"
)
if settings.SWEEPER_ENABLED:
    celery_app.conf.beat_schedule = {
        "sweep-stale-jobs": {
            "task": "memory_allocator.sweep_stale_jobs",
            "schedule": float(settings.SWEEPER_INTERVAL_SECONDS),
            "options": {"expires": settings.SWEEPER_INTERVAL_SECONDS},
        }
    }
celery_app.autodiscover_tasks(["app.memory_allocator"])
