import logging
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch

import pytest

from app.core.celery_app import celery_app
from app.core.config import get_settings
from app.memory_allocator.services.deadletter_service import DeadLetterService
from app.memory_allocator.tasks import tasks_dlq


@asynccontextmanager
async def _fake_uow(uow):
    yield uow


@asynccontextmanager
async def _fake_bus():
    yield Mock()


def make_raw(headers=None, body=b'[[7], {}, {"callbacks": null}]', delivery_tag=1):
    return SimpleNamespace(
        headers=headers,
        body=body,
        content_type="application/json",
        content_encoding="utf-8",
        delivery_tag=delivery_tag,
    )


@pytest.fixture
def patched_drain(mock_uow):
    service = Mock(spec=DeadLetterService)
    service.record.return_value = 1
    connection = MagicMock()
    channel = connection.__enter__.return_value.default_channel
    with patch.object(tasks_dlq, "build_uow", lambda: _fake_uow(mock_uow)), \
         patch.object(tasks_dlq, "build_event_bus", _fake_bus), \
         patch.object(tasks_dlq, "DeadLetterService", return_value=service), \
         patch.object(celery_app, "connection_for_write", return_value=connection):
        yield service, channel


def test_drains_all_messages(patched_drain):
    service, channel = patched_drain
    channel.basic_get.side_effect = [make_raw(delivery_tag=11), make_raw(delivery_tag=22), None]

    drained = tasks_dlq.drain_dlq()

    assert drained == 2
    assert service.record.await_count == 2
    assert [c.args[0] for c in channel.basic_ack.call_args_list] == [11, 22]


def test_returns_zero_on_empty_queue(patched_drain, caplog):
    service, channel = patched_drain
    channel.basic_get.return_value = None

    with caplog.at_level(logging.INFO, logger=tasks_dlq.logger.name):
        drained = tasks_dlq.drain_dlq()

    assert drained == 0
    service.record.assert_not_awaited()
    channel.basic_ack.assert_not_called()
    assert caplog.records == []


def test_acknowledges_after_record(patched_drain):
    service, channel = patched_drain
    channel.basic_get.side_effect = [make_raw(), None]

    manager = Mock()
    manager.attach_mock(service.record, "record")
    manager.attach_mock(channel.basic_ack, "ack")

    tasks_dlq.drain_dlq()

    assert [call[0] for call in manager.mock_calls] == ["record", "ack"]


def test_does_not_acknowledge_when_record_fails(patched_drain):
    service, channel = patched_drain
    channel.basic_get.side_effect = [make_raw(), None]
    service.record.side_effect = RuntimeError("db is down")

    with pytest.raises(RuntimeError, match="db is down"):
        tasks_dlq.drain_dlq()

    channel.basic_ack.assert_not_called()


def test_respects_batch_limit(patched_drain):
    service, channel = patched_drain
    channel.basic_get.return_value = make_raw()

    drained = tasks_dlq.drain_dlq()

    assert drained == get_settings().DLQ_BATCH_LIMIT
    assert service.record.await_count == get_settings().DLQ_BATCH_LIMIT


def test_parses_full_envelope():
    raw = make_raw(headers={
        "task": "memory_allocator.process_test",
        "id": "task-uuid",
        "request_id": "rid-1",
        "x-last-death-reason": "delivery_limit",
        "x-death": [{"count": 3, "reason": "delivery_limit"}],
    })

    message = tasks_dlq._parse_envelope(raw)

    assert message.task_name == "memory_allocator.process_test"
    assert message.task_id == "task-uuid"
    assert message.args == [7]
    assert message.request_id == "rid-1"
    assert message.reason == "delivery_limit"
    assert message.delivered_count == 3


def test_parses_bare_envelope():
    message = tasks_dlq._parse_envelope(make_raw(headers={}))

    assert message.task_name == "unknown"
    assert message.task_id == "unknown"
    assert message.request_id is None
    assert message.reason is None
    assert message.delivered_count is None


def test_parses_envelope_without_headers():
    message = tasks_dlq._parse_envelope(make_raw(headers=None))

    assert message.task_name == "unknown"


def test_survives_empty_x_death():
    message = tasks_dlq._parse_envelope(make_raw(headers={"task": "t", "id": "i", "x-death": []}))

    assert message.delivered_count is None


@pytest.mark.parametrize("body", [b"[]", b'"garbage"', b"{}"])
def test_survives_unexpected_body(body):
    message = tasks_dlq._parse_envelope(make_raw(headers={"task": "t", "id": "i"}, body=body))

    assert message.args is None
