import json
from unittest.mock import AsyncMock

import pytest

from app.memory_allocator.notifications import StatusNotifier
from tests.factories import make_test, make_validation_result


@pytest.mark.asyncio
async def test_publish_correct_channel(mock_bus):
    test = make_test(id=4)
    notifier = StatusNotifier(mock_bus)
    await notifier.test_status_changed(test)

    mock_bus.publish.assert_awaited_once()
    assert mock_bus.publish.await_args.args[0] == "test:4"


@pytest.mark.asyncio
async def test_publish_test_status_changed(mock_bus):
    test = make_test(status="error", error_message="low_ram")
    notifier = StatusNotifier(mock_bus)
    await notifier.test_status_changed(test)

    mock_bus.publish.assert_awaited_once()
    assert mock_bus.publish.await_args.args[0] == "test:1"
    payload = json.loads(mock_bus.publish.await_args.args[1])
    assert payload["event"] == "test.status"
    assert payload["test_id"] == 1
    assert payload["status"] == "error"
    assert payload["error_message"] == "low_ram"
    assert payload["ts"] is not None


@pytest.mark.asyncio
async def test_publish_validation_status_changed(mock_bus):
    vr = make_validation_result(id=7, test_id=2, status="completed", valid=False, schema_valid=True)
    notifier = StatusNotifier(mock_bus)
    await notifier.validation_status_changed(vr)

    mock_bus.publish.assert_awaited_once()
    assert mock_bus.publish.await_args.args[0] == "test:2"
    payload = json.loads(mock_bus.publish.await_args.args[1])
    assert payload["event"] == "validation.status"
    assert payload["test_id"] == 2
    assert payload["validation_id"] == 7
    assert payload["status"] == "completed"
    assert payload["valid"] is False
    assert payload["ts"] is not None


@pytest.mark.asyncio
async def test_publish_not_raises_exception(mock_bus):
    test = make_test()
    vr = make_validation_result(test_id=test.id)
    mock_bus.publish = AsyncMock(side_effect=ConnectionError("boom"))
    notifier = StatusNotifier(mock_bus)
    await notifier.test_status_changed(test)
    await notifier.validation_status_changed(vr)


@pytest.mark.asyncio
async def test_publish_test_status_changed_logs(mock_bus, caplog):
    mock_bus.publish = AsyncMock(side_effect=ConnectionError("boom"))
    test = make_test(status="error", error_message="low_ram")
    notifier = StatusNotifier(mock_bus)
    await notifier.test_status_changed(test)

    mock_bus.publish.assert_awaited_once()
    failures = [r for r in caplog.records if r.getMessage() == "event.publish_failed"]
    assert len(failures) == 1
    record = failures[0]
    assert record.levelname == "WARNING"
    assert record.channel == "test:1"
    assert record.event == "test.status"
    assert record.status == "error"
    assert "boom" in record.error


@pytest.mark.asyncio
async def test_publish_validation_status_changed_logs(mock_bus, caplog):
    mock_bus.publish = AsyncMock(side_effect=ConnectionError("boom"))
    vr = make_validation_result(id=7, test_id=2, status="completed", valid=False, schema_valid=True)
    notifier = StatusNotifier(mock_bus)
    await notifier.validation_status_changed(vr)

    mock_bus.publish.assert_awaited_once()
    failures = [r for r in caplog.records if r.getMessage() == "event.publish_failed"]
    assert len(failures) == 1
    record = failures[0]
    assert record.levelname == "WARNING"
    assert record.channel == "test:2"
    assert record.event == "validation.status"
    assert record.status == "completed"
    assert "boom" in record.error
