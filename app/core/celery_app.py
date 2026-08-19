from celery import Celery
from kombu import Exchange, Queue

import app.core.celery_signals  # noqa: F401
from app.core.config import get_settings

settings = get_settings()

DEAD_LETTER_QUEUE = "dlq"
DEAD_LETTER_EXCHANGE = "dlx"
DEAD_LETTER_ROUTING_KEY = "dead"
beat_schedule: dict[str, dict] = {}

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
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    timezone="UTC"
)
if settings.SWEEPER_ENABLED:
    beat_schedule["sweep-stale-jobs"] = {
            "task": "memory_allocator.sweep_stale_jobs",
            "schedule": float(settings.SWEEPER_INTERVAL_SECONDS),
            "options": {"expires": settings.SWEEPER_INTERVAL_SECONDS},
        }
if settings.DLQ_DRAIN_ENABLED:
    beat_schedule["drain-dlq"] = {
        "task": "memory_allocator.drain_dlq",
        "schedule": float(settings.DLQ_DRAIN_INTERVAL_SECONDS),
        "options": {"expires": settings.DLQ_DRAIN_INTERVAL_SECONDS},
    }
celery_app.conf.beat_schedule = beat_schedule
celery_app.conf.task_queues = [
    Queue(
        "celery",
        Exchange("celery", type="topic"),
        routing_key="celery",
        queue_arguments={
            "x-queue-type": "quorum",
            "x-delivery-limit": settings.TASK_DELIVERY_LIMIT,
            "x-dead-letter-exchange": DEAD_LETTER_EXCHANGE,
            "x-dead-letter-routing-key": DEAD_LETTER_ROUTING_KEY,
        },
    ),
]
celery_app.autodiscover_tasks(["app.memory_allocator"])
