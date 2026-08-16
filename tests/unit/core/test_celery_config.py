import pytest

from app.core.celery_app import celery_app
from app.core.config import get_settings

SWEEPER_ENTRY = "sweep-stale-jobs"


@pytest.fixture
def registered_tasks():
    celery_app.loader.import_default_modules()
    return celery_app.tasks


def test_beat_schedule_has_sweeper_entry():
    settings = get_settings()
    entry = celery_app.conf.beat_schedule[SWEEPER_ENTRY]

    assert entry["schedule"] == float(settings.SWEEPER_INTERVAL_SECONDS)
    assert entry["options"]["expires"] == settings.SWEEPER_INTERVAL_SECONDS


def test_scheduled_task_name_is_registered(registered_tasks):
    scheduled_name = celery_app.conf.beat_schedule[SWEEPER_ENTRY]["task"]

    assert scheduled_name in registered_tasks


def test_worker_tasks_are_registered(registered_tasks):
    assert "memory_allocator.process_test" in registered_tasks
    assert "memory_allocator.process_validation" in registered_tasks


def test_timezone_is_utc():
    assert celery_app.conf.timezone == "UTC"
