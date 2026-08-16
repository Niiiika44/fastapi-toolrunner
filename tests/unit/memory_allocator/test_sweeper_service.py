import logging
from datetime import UTC, datetime, timedelta
from unittest.mock import Mock

import pytest

from app.memory_allocator.enums import TestStatus
from app.memory_allocator.services.sweeper_service import SweeperService
from tests.factories import make_test, make_validation_result


@pytest.mark.asyncio
async def test_requeue_stale_pending_success(mock_uow):
    dispatch = Mock()
    dispatch_validation = Mock()
    service = SweeperService(mock_uow, dispatch, dispatch_validation)
    test_1 = make_test(id=1, status=TestStatus.PENDING)
    test_2 = make_test(id=2, status=TestStatus.PENDING)
    test_3 = make_test(id=3, status=TestStatus.PENDING)
    mock_uow.tests.find_stale_pending.return_value = [test_1, test_2, test_3]

    count = await service.requeue_stale_pending(timedelta(seconds=900), limit=3)

    assert count == 3
    requeued_ids = [c.args[0] for c in dispatch.call_args_list]
    assert requeued_ids == [1, 2, 3]
    dispatch_validation.assert_not_called()
    mock_uow.commit.assert_not_awaited()
    mock_uow.rollback.assert_not_awaited()


@pytest.mark.asyncio
async def test_requeue_stale_pending_success_on_empty(mock_uow, caplog):
    dispatch = Mock()
    dispatch_validation = Mock()
    service = SweeperService(mock_uow, dispatch, dispatch_validation)
    mock_uow.tests.find_stale_pending.return_value = []

    with caplog.at_level(logging.INFO):
        count = await service.requeue_stale_pending(timedelta(seconds=900), limit=3)

    assert count == 0
    mock_uow.commit.assert_not_awaited()
    mock_uow.rollback.assert_not_awaited()
    dispatch.assert_not_called()
    requeued_log = [r for r in caplog.records if r.getMessage() == "sweeper.requeued"]
    assert requeued_log == []


@pytest.mark.asyncio
async def test_requeue_stale_pending_correct_params(mock_uow):
    dispatch = Mock()
    dispatch_validation = Mock()
    service = SweeperService(mock_uow, dispatch, dispatch_validation)
    mock_uow.tests.find_stale_pending.return_value = [make_test(id=1, status=TestStatus.PENDING)]

    count = await service.requeue_stale_pending(timedelta(seconds=900), limit=3)

    assert count == 1
    mock_uow.commit.assert_not_awaited()
    mock_uow.rollback.assert_not_awaited()
    assert mock_uow.tests.find_stale_pending.await_args.kwargs["limit"] == 3
    older_than = mock_uow.tests.find_stale_pending.await_args.kwargs["older_than"]
    assert older_than - datetime.now(UTC) < timedelta(minutes=1)
    dispatch.assert_called_once()


@pytest.mark.asyncio
async def test_requeue_stale_pending_one_problem_test_success(mock_uow, caplog):
    dispatch = Mock()
    dispatch_validation = Mock()
    service = SweeperService(mock_uow, dispatch, dispatch_validation)
    test_1 = make_test(id=1, status=TestStatus.PENDING)
    test_2 = make_test(id=2, status=TestStatus.PENDING)
    test_3 = make_test(id=3, status=TestStatus.PENDING)
    mock_uow.tests.find_stale_pending.return_value = [test_1, test_2, test_3]
    dispatch.side_effect = [None, RuntimeError, None]

    with caplog.at_level(logging.INFO):
        count = await service.requeue_stale_pending(timedelta(seconds=900), limit=3)

    assert count == 2
    mock_uow.commit.assert_not_awaited()
    mock_uow.rollback.assert_not_awaited()
    assert dispatch.call_count == 3
    enqueue_failed_log = [r for r in caplog.records if r.getMessage() == "sweeper.enqueue_failed"]
    assert len(enqueue_failed_log) == 1
    assert enqueue_failed_log[0].item_id == 2
    assert enqueue_failed_log[0].error == "RuntimeError()"
    enqueue_log = [r for r in caplog.records if r.getMessage() == "sweeper.requeued"]
    assert len(enqueue_log) == 1
    assert enqueue_log[0].ids == [1, 3]
    assert enqueue_log[0].count == 2
    assert enqueue_log[0].kind == "tests"
    assert enqueue_log[0].failed == 1


@pytest.mark.asyncio
async def test_requeue_stale_pending_fails_on_runtime_error(mock_uow, caplog):
    dispatch = Mock()
    dispatch_validation = Mock()
    service = SweeperService(mock_uow, dispatch, dispatch_validation)
    mock_uow.tests.find_stale_pending.return_value = [make_test(id=1, status=TestStatus.PENDING)]
    dispatch.side_effect = [RuntimeError]

    with caplog.at_level(logging.INFO), pytest.raises(RuntimeError):
        await service.requeue_stale_pending(timedelta(seconds=900), limit=3)
    assert "sweeper.requeued" not in [r.getMessage() for r in caplog.records]


@pytest.mark.asyncio
async def test_requeue_stale_validations_uses_its_own_dispatcher(mock_uow):
    dispatch = Mock()
    dispatch_validation = Mock()
    service = SweeperService(mock_uow, dispatch, dispatch_validation)
    mock_uow.validations.find_stale_pending.return_value = [
        make_validation_result(id=7), make_validation_result(id=9)
    ]

    count = await service.requeue_stale_validations(timedelta(seconds=900), limit=3)

    assert count == 2
    assert [c.args[0] for c in dispatch_validation.call_args_list] == [7, 9]
    dispatch.assert_not_called()
    mock_uow.commit.assert_not_awaited()
    mock_uow.rollback.assert_not_awaited()


@pytest.mark.asyncio
async def test_requeue_stale_validations_success_on_empty(mock_uow, caplog):
    dispatch = Mock()
    dispatch_validation = Mock()
    service = SweeperService(mock_uow, dispatch, dispatch_validation)
    mock_uow.validations.find_stale_pending.return_value = []

    with caplog.at_level(logging.INFO):
        count = await service.requeue_stale_validations(timedelta(seconds=900), limit=3)

    assert count == 0
    dispatch_validation.assert_not_called()
    assert "sweeper.requeued" not in [r.getMessage() for r in caplog.records]


@pytest.mark.asyncio
async def test_requeue_stale_validations_correct_params(mock_uow, caplog):
    dispatch = Mock()
    dispatch_validation = Mock()
    service = SweeperService(mock_uow, dispatch, dispatch_validation)
    mock_uow.validations.find_stale_pending.return_value = [make_validation_result(id=7)]

    with caplog.at_level(logging.INFO):
        await service.requeue_stale_validations(timedelta(seconds=900), limit=3)

    kwargs = mock_uow.validations.find_stale_pending.await_args.kwargs
    assert kwargs["limit"] == 3
    assert datetime.now(UTC) - kwargs["older_than"] - timedelta(seconds=900) < timedelta(minutes=1)
    mock_uow.tests.find_stale_pending.assert_not_awaited()
    requeued_log = [r for r in caplog.records if r.getMessage() == "sweeper.requeued"]
    assert requeued_log[0].kind == "validations"
