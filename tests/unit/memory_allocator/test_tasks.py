from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.memory_allocator import tasks
from app.memory_allocator.enums import TestStatus
from app.memory_allocator.exceptions import ParsingError
from app.memory_allocator.services.ingestion_service import IngestionService


@asynccontextmanager
async def _fake_uow(uow):
    yield uow


@pytest.mark.asyncio
async def test_process_test_happy(mock_uow, mock_storage):
    test = Mock()
    mock_uow.tests.find_for_processing.return_value = test
    mock_storage.load.return_value = b"zip-bytes"

    fake_service = IngestionService(mock_uow, mock_storage)
    fake_service.process_upload = AsyncMock()

    with patch.object(tasks, "build_uow", lambda: _fake_uow(mock_uow)), \
         patch.object(tasks, "get_storage", return_value=mock_storage), \
         patch.object(tasks, "IngestionService", return_value=fake_service):
        await tasks._process_test(1)

    assert test.status == tasks.TestStatus.PROCESSING
    mock_uow.commit.assert_awaited_once()
    mock_storage.load.assert_awaited_once_with("uploads/1.zip")
    fake_service.process_upload.assert_awaited_once_with(test, b"zip-bytes")


@pytest.mark.asyncio
async def test_process_test_not_found(mock_uow, mock_storage):
    mock_uow.tests.find_for_processing.return_value = None
    with patch.object(tasks, "build_uow", lambda: _fake_uow(mock_uow)), \
         patch.object(tasks, "get_storage", return_value=mock_storage):
        await tasks._process_test(1)
    mock_uow.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_process_test_domain_error(mock_uow, mock_storage):
    test = Mock()
    mock_uow.tests.find_for_processing.return_value = test
    mock_storage.load.return_value = b"zip-bytes"
    fake_service = Mock()
    fake_service.process_upload = AsyncMock()
    fake_service.process_upload.side_effect = ParsingError("x")
    with patch.object(tasks, "get_storage", return_value=mock_storage), \
         patch.object(tasks, "build_uow", lambda: _fake_uow(mock_uow)), \
         patch.object(tasks, "IngestionService", return_value=fake_service):
        await tasks._process_test(1)
    mock_uow.rollback.assert_awaited_once()
    assert test.status == TestStatus.ERROR
    assert test.error_message == "File could not be parsed: x"
    assert mock_uow.commit.call_count == 2


@pytest.mark.asyncio
async def test_process_test_infra_error(mock_uow, mock_storage):
    test = Mock()
    mock_uow.tests.find_for_processing.return_value = test
    mock_storage.load.return_value = b"zip-bytes"
    fake_service = Mock()
    fake_service.process_upload = AsyncMock()
    fake_service.process_upload.side_effect = RuntimeError("x")
    with patch.object(tasks, "get_storage", return_value=mock_storage), \
         patch.object(tasks, "build_uow", lambda: _fake_uow(mock_uow)), \
         patch.object(tasks, "IngestionService", return_value=fake_service):
        with pytest.raises(RuntimeError):
            await tasks._process_test(1)
    mock_uow.rollback.assert_awaited_once()
    assert test.status == TestStatus.PROCESSING
    assert mock_uow.commit.call_count == 1
    mock_storage.delete.assert_not_awaited()


@pytest.mark.asyncio
async def test_process_test_skips_when_parsed(mock_uow):
    test = Mock()
    test.status = "parsed"
    mock_uow.tests.find_for_processing.return_value = test
    fake_service = Mock()
    fake_service.process_upload = AsyncMock()
    with patch.object(tasks, "build_uow", lambda: _fake_uow(mock_uow)), \
         patch.object(tasks, "IngestionService", return_value=fake_service):
        await tasks._process_test(1)
    mock_uow.commit.assert_not_awaited()
    fake_service.process_upload.assert_not_called()


@pytest.mark.asyncio
async def test_process_test_deletes_zip_on_success(mock_uow, mock_storage):
    test = Mock()
    mock_uow.tests.find_for_processing.return_value = test
    mock_storage.load.return_value = b"zip-bytes"

    fake_service = IngestionService(mock_uow, mock_storage)
    fake_service.process_upload = AsyncMock()

    with patch.object(tasks, "build_uow", lambda: _fake_uow(mock_uow)), \
         patch.object(tasks, "get_storage", return_value=mock_storage), \
         patch.object(tasks, "IngestionService", return_value=fake_service):
        await tasks._process_test(1)

    assert test.status == tasks.TestStatus.PROCESSING
    mock_uow.commit.assert_awaited_once()
    mock_storage.delete.assert_awaited_once_with("uploads/1.zip")