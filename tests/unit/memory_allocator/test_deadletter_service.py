import logging
from unittest.mock import Mock

import pytest

from app.memory_allocator.enums import TestStatus, ValidationStatus
from app.memory_allocator.services.deadletter_service import DeadLetterService
from tests.factories import make_message, make_test, make_validation_result


def _simulate_db_refresh(letter):
    if letter.id is None:
        letter.id = 1


@pytest.mark.asyncio
async def test_records_terminates_test(mock_uow, mock_notifier):
    letter_message = make_message(task_name="memory_allocator.process_test")
    test = make_test(id=7, status=TestStatus.PENDING)
    service = DeadLetterService(mock_uow, mock_notifier)
    mock_uow.dead_letters.add.side_effect = _simulate_db_refresh
    mock_uow.tests.find_by_id.return_value = test

    letter_id = await service.record(letter_message)

    letter = mock_uow.dead_letters.add.call_args.args[0]
    assert letter.task_name == letter_message.task_name
    assert letter.task_id == letter_message.task_id
    assert letter.args == letter_message.args
    assert letter.request_id == letter_message.request_id
    assert letter.reason == letter_message.reason
    assert letter.delivered_count == letter_message.delivered_count
    assert letter_id == letter.id
    assert test.status == TestStatus.ERROR
    assert letter_message.reason in test.error_message
    assert mock_uow.commit.await_count == 1
    mock_uow.rollback.assert_not_awaited()


@pytest.mark.asyncio
async def test_records_terminates_validation(mock_uow, mock_notifier):
    letter_message = make_message(task_name="memory_allocator.process_validation")
    vr = make_validation_result(status=ValidationStatus.PENDING)
    service = DeadLetterService(mock_uow, mock_notifier)
    mock_uow.dead_letters.add.side_effect = _simulate_db_refresh
    mock_uow.validations.find_by_id.return_value = vr

    letter_id = await service.record(letter_message)

    mock_uow.tests.find_by_id.assert_not_awaited()
    letter = mock_uow.dead_letters.add.call_args.args[0]
    assert letter.task_name == letter_message.task_name
    assert letter.task_id == letter_message.task_id
    assert letter.args == letter_message.args
    assert letter.request_id == letter_message.request_id
    assert letter.reason == letter_message.reason
    assert letter.delivered_count == letter_message.delivered_count
    assert letter_id == letter.id
    assert vr.status == ValidationStatus.FAILED
    assert mock_uow.commit.await_count == 1
    mock_uow.rollback.assert_not_awaited()


@pytest.mark.asyncio
async def test_records_keeps_finished_test_untouched(mock_uow, mock_notifier, caplog):
    letter_message = make_message(task_name="memory_allocator.process_test")
    test = make_test(id=7, status=TestStatus.PARSED)
    service = DeadLetterService(mock_uow, mock_notifier)
    mock_uow.dead_letters.add.side_effect = _simulate_db_refresh
    mock_uow.tests.find_by_id.return_value = test

    await service.record(letter_message)

    assert test.status == TestStatus.PARSED
    log_entry = [r for r in caplog.records if r.getMessage() == "dlq.recorded"]
    assert log_entry[0].terminated is False


@pytest.mark.asyncio
async def test_records_keeps_finished_validation_untouched(mock_uow, mock_notifier, caplog):
    letter_message = make_message(task_name="memory_allocator.process_validation")
    vr = make_validation_result(status=ValidationStatus.COMPLETED)
    service = DeadLetterService(mock_uow, mock_notifier)
    mock_uow.dead_letters.add.side_effect = _simulate_db_refresh
    mock_uow.validations.find_by_id.return_value = vr

    await service.record(letter_message)

    assert vr.status == ValidationStatus.COMPLETED
    log_entry = [r for r in caplog.records if r.getMessage() == "dlq.recorded"]
    assert log_entry[0].terminated is False


@pytest.mark.asyncio
async def test_records_unknown_task(mock_uow, mock_notifier):
    letter_message = make_message(task_name="memory_allocator.new_taskname")
    service = DeadLetterService(mock_uow, mock_notifier)

    letter_id = await service.record(letter_message)

    letter = mock_uow.dead_letters.add.call_args.args[0]
    assert letter.task_name == letter_message.task_name
    assert letter.task_id == letter_message.task_id
    assert letter.args == letter_message.args
    assert letter.request_id == letter_message.request_id
    assert letter.reason == letter_message.reason
    assert letter.delivered_count == letter_message.delivered_count
    assert letter_id == letter.id
    assert mock_uow.commit.await_count == 1
    mock_uow.tests.find_by_id.assert_not_awaited()
    mock_uow.validations.find_by_id.assert_not_awaited()
    mock_uow.rollback.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("args", [
    [],
    ["not_int"]
])
async def test_records_unknown_owner_id(args, mock_uow, mock_notifier, caplog):
    letter_message = make_message(task_name="memory_allocator.process_test", args=args)
    service = DeadLetterService(mock_uow, mock_notifier)

    with caplog.at_level(logging.INFO):
        letter_id = await service.record(letter_message)

    letter = mock_uow.dead_letters.add.call_args.args[0]
    assert letter.task_name == letter_message.task_name
    assert letter.task_id == letter_message.task_id
    assert letter.args == letter_message.args
    assert letter.request_id == letter_message.request_id
    assert letter.reason == letter_message.reason
    assert letter.delivered_count == letter_message.delivered_count
    assert letter_id == letter.id
    assert mock_uow.commit.await_count == 1
    mock_uow.tests.find_by_id.assert_not_awaited()
    mock_uow.validations.find_by_id.assert_not_awaited()
    mock_uow.rollback.assert_not_awaited()
    log_entry = [r for r in caplog.records if r.getMessage() == "dlq.owner_unknown"]
    assert len(log_entry) == 1


@pytest.mark.asyncio
async def test_records_publishes_after_commit(mock_uow, mock_notifier):
    letter_message = make_message(task_name="memory_allocator.process_test")
    test = make_test(id=7, status=TestStatus.PROCESSING)
    service = DeadLetterService(mock_uow, mock_notifier)
    mock_uow.dead_letters.add.side_effect = _simulate_db_refresh
    mock_uow.tests.find_by_id.return_value = test

    manager = Mock()
    manager.attach_mock(mock_uow.commit, "commit")
    manager.attach_mock(mock_notifier.test_status_changed, "publish")

    await service.record(letter_message)

    assert [call[0] for call in manager.mock_calls] == ["commit", "publish"]


@pytest.mark.asyncio
async def test_records_works_without_notifier(mock_uow):
    letter_message = make_message(task_name="memory_allocator.process_test")
    test = make_test(id=7, status=TestStatus.PROCESSING)
    service = DeadLetterService(mock_uow)
    mock_uow.dead_letters.add.side_effect = _simulate_db_refresh
    mock_uow.tests.find_by_id.return_value = test

    letter_id = await service.record(letter_message)

    assert letter_id == 1
    assert test.status == TestStatus.ERROR
    assert mock_uow.commit.await_count == 1
    mock_uow.rollback.assert_not_awaited()


@pytest.mark.asyncio
async def test_records_falls_back_when_reason_unknown(mock_uow, mock_notifier):
    letter_message = make_message(task_name="memory_allocator.process_test", reason=None)
    test = make_test(id=7, status=TestStatus.PROCESSING)
    service = DeadLetterService(mock_uow, mock_notifier)
    mock_uow.dead_letters.add.side_effect = _simulate_db_refresh
    mock_uow.tests.find_by_id.return_value = test

    await service.record(letter_message)

    assert "unknown" in test.error_message
    assert "None" not in test.error_message
    mock_uow.rollback.assert_not_awaited()
