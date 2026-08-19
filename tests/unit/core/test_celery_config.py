from unittest.mock import MagicMock, patch

import pytest

from app.core.celery_app import celery_app
from app.core.celery_signals import _declare_dead_letter_queue
from app.core.config import get_settings

SWEEPER_ENTRY = "sweep-stale-jobs"
DLQ_ENTRY = "drain-dlq"
WORK_QUEUE = "celery"
DEAD_LETTER_QUEUE = "dlq"


@pytest.fixture
def registered_tasks():
    celery_app.loader.import_default_modules()
    return celery_app.tasks


@pytest.fixture
def work_queue():
    queues = {queue.name: queue for queue in celery_app.conf.task_queues}
    return queues[WORK_QUEUE]


@pytest.fixture
def declared_channel():
    connection = MagicMock()
    with patch.object(celery_app, "connection_for_write", return_value=connection):
        _declare_dead_letter_queue()
    return connection.__enter__.return_value.default_channel


def test_beat_schedule_has_sweeper_entry():
    settings = get_settings()
    entry = celery_app.conf.beat_schedule[SWEEPER_ENTRY]

    assert entry["schedule"] == float(settings.SWEEPER_INTERVAL_SECONDS)
    assert entry["options"]["expires"] == settings.SWEEPER_INTERVAL_SECONDS


def test_beat_schedule_has_dlq_entry():
    settings = get_settings()
    entry = celery_app.conf.beat_schedule[DLQ_ENTRY]

    assert entry["schedule"] == float(settings.DLQ_DRAIN_INTERVAL_SECONDS)
    assert entry["options"]["expires"] == settings.DLQ_DRAIN_INTERVAL_SECONDS


def test_scheduled_task_name_is_registered(registered_tasks):
    scheduled_name_sweeper = celery_app.conf.beat_schedule[SWEEPER_ENTRY]["task"]
    scheduled_name_dlq = celery_app.conf.beat_schedule[DLQ_ENTRY]["task"]

    assert scheduled_name_sweeper in registered_tasks
    assert scheduled_name_dlq in registered_tasks


def test_worker_tasks_are_registered(registered_tasks):
    assert "memory_allocator.process_test" in registered_tasks
    assert "memory_allocator.process_validation" in registered_tasks


def test_timezone_is_utc():
    assert celery_app.conf.timezone == "UTC"


def test_work_queue_counts_deliveries_and_dead_letters(work_queue):
    settings = get_settings()
    arguments = work_queue.queue_arguments

    assert work_queue.exchange.type == "topic"
    assert arguments["x-queue-type"] == "quorum"
    assert arguments["x-delivery-limit"] == settings.TASK_DELIVERY_LIMIT
    assert arguments["x-dead-letter-exchange"] == "dlx"
    assert arguments["x-dead-letter-routing-key"] == "dead"


def test_worker_death_does_not_acknowledge_message():
    assert celery_app.conf.task_reject_on_worker_lost is True


def test_dead_letter_queue_is_not_consumed():
    consumed = {queue.name for queue in celery_app.conf.task_queues}

    assert DEAD_LETTER_QUEUE not in consumed


def test_dead_letter_queue_is_declared_with_binding(declared_channel):
    assert declared_channel.exchange_declare.call_args.kwargs["exchange"] == "dlx"
    assert declared_channel.exchange_declare.call_args.kwargs["type"] == "direct"
    assert declared_channel.queue_declare.call_args.kwargs["queue"] == DEAD_LETTER_QUEUE
    assert declared_channel.queue_declare.call_args.kwargs["durable"] is True
    assert declared_channel.queue_bind.call_args.kwargs == {
        "queue": DEAD_LETTER_QUEUE,
        "exchange": "dlx",
        "routing_key": "dead",
        "arguments": None,
        "nowait": False,
    }


def test_dead_letters_land_where_work_queue_sends_them(work_queue, declared_channel):
    binding = declared_channel.queue_bind.call_args.kwargs

    assert binding["exchange"] == work_queue.queue_arguments["x-dead-letter-exchange"]
    assert binding["routing_key"] == work_queue.queue_arguments["x-dead-letter-routing-key"]
