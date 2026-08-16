import logging
from contextlib import asynccontextmanager
from datetime import timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.core.config import get_settings
from app.memory_allocator.services import SweeperService
from app.memory_allocator.tasks import process_test, tasks_sweeper


@asynccontextmanager
async def _fake_uow(uow):
    yield uow


@pytest.fixture
def patched_sweeper(mock_uow):
    service = Mock(spec=SweeperService)
    service.requeue_stale_pending.return_value = 0
    with patch.object(tasks_sweeper, "build_uow", lambda: _fake_uow(mock_uow)), \
         patch.object(tasks_sweeper, "SweeperService", return_value=service):
        yield service


@pytest.mark.asyncio
async def test_sweep_happy(mock_uow):
    dispatch = Mock()
    fake_service = SweeperService(mock_uow, dispatch)
    fake_service.requeue_stale_pending = AsyncMock()
    fake_service.requeue_stale_pending.return_value = 3

    with patch.object(tasks_sweeper, "build_uow", lambda: _fake_uow(mock_uow)), \
         patch.object(tasks_sweeper, "SweeperService", return_value=fake_service) as service_cls:
        requeued_num = await tasks_sweeper._sweep()

    assert requeued_num == 3
    assert service_cls.call_args.args[1] == process_test.delay


def test_task_returns_service_count(patched_sweeper):
    patched_sweeper.requeue_stale_pending.return_value = 3

    assert tasks_sweeper.sweep_stale_jobs() == 3


def test_task_passes_settings_to_service(patched_sweeper):
    settings = get_settings()

    tasks_sweeper.sweep_stale_jobs()

    kwargs = patched_sweeper.requeue_stale_pending.await_args.kwargs
    assert kwargs["stale_after"] == timedelta(seconds=settings.SWEEPER_STALE_AFTER_SECONDS)
    assert kwargs["limit"] == settings.SWEEPER_BATCH_LIMIT


def test_task_does_not_swallow_service_error(patched_sweeper):
    patched_sweeper.requeue_stale_pending.side_effect = RuntimeError("broker down")

    with pytest.raises(RuntimeError, match="broker down"):
        tasks_sweeper.sweep_stale_jobs()


def test_task_logs_finish_at_info_when_something_requeued(patched_sweeper, caplog):
    patched_sweeper.requeue_stale_pending.return_value = 2

    with caplog.at_level(logging.INFO, logger=tasks_sweeper.logger.name):
        tasks_sweeper.sweep_stale_jobs()

    finished = [r for r in caplog.records if r.message == "task.finished"]
    assert len(finished) == 1
    assert finished[0].levelno == logging.INFO
    assert finished[0].requeued == 2


def test_task_stays_quiet_at_info_when_nothing_requeued(patched_sweeper, caplog):
    patched_sweeper.requeue_stale_pending.return_value = 0

    with caplog.at_level(logging.INFO, logger=tasks_sweeper.logger.name):
        tasks_sweeper.sweep_stale_jobs()

    assert caplog.records == []
