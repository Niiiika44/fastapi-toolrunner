from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, patch

import pytest

from app.memory_allocator.enums import ValidationStatus
from app.memory_allocator.services.validation_service import ValidationService
from app.memory_allocator.tasks import tasks_validation
from tests.factories import make_validation_result


@asynccontextmanager
async def _fake_uow(uow):
    yield uow


@pytest.mark.asyncio
async def test_process_validation_happy(mock_uow, mock_checker):
    fake_service = ValidationService(mock_uow, mock_checker)
    fake_service.perform_validation = AsyncMock()

    with patch.object(tasks_validation, "build_uow", lambda: _fake_uow(mock_uow)), \
         patch.object(tasks_validation, "ValidationService", return_value=fake_service):
        await tasks_validation._process_validation(1)

    fake_service.perform_validation.assert_awaited_once_with(1)


@pytest.mark.asyncio
async def test_process_validation_propagates_error(mock_uow, mock_checker):
    fake_service = ValidationService(mock_uow, mock_checker)
    fake_service.perform_validation = AsyncMock(side_effect=RuntimeError("x"))

    with patch.object(tasks_validation, "build_uow", lambda: _fake_uow(mock_uow)), \
         patch.object(tasks_validation, "ValidationService", return_value=fake_service):
        with pytest.raises(RuntimeError):
            await tasks_validation._process_validation(1)

    mock_uow.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_mark_failed_sets_failed(mock_uow):
    vr = make_validation_result(status=ValidationStatus.RUNNING)
    mock_uow.validations.find_by_id.return_value = vr

    with patch.object(tasks_validation, "build_uow", lambda: _fake_uow(mock_uow)):
        await tasks_validation._mark_failed(1)

    assert vr.status == ValidationStatus.FAILED
    mock_uow.commit.assert_awaited_once()
