import zipfile
from unittest.mock import Mock

import pytest

from app.memory_allocator.enums import TestStatus
from app.memory_allocator.exceptions import ExportNotAvailableError, TestNotFoundError
from app.memory_allocator.services.export_service import ExportService
from tests.factories import make_test


def _make_service(mock_uow, mock_storage):
    return ExportService(uow=mock_uow, storage=mock_storage)


def _artifact(filename: str) -> Mock:
    return Mock(filename=filename, storage_key=f"artifacts/1/{filename}")


@pytest.mark.asyncio
async def test_export_test_success(mock_uow, mock_storage):
    test = make_test(status=TestStatus.PARSED, name="mips")
    service = _make_service(mock_uow, mock_storage)
    mock_uow.tests.find_by_id.return_value = test
    mock_uow.artifacts.list_by_test.return_value = [
        _artifact("memin.yaml"),
        _artifact("status.yaml"),
    ]
    mock_storage.load.return_value = b"file-bytes"

    buffer, filename = await service.export_test(test.id)

    assert filename == "mips.zip"
    with zipfile.ZipFile(buffer) as zf:
        assert set(zf.namelist()) == {"memin.yaml", "status.yaml"}
        assert zf.read("memin.yaml") == b"file-bytes"


@pytest.mark.asyncio
async def test_export_test_not_found(mock_uow, mock_storage):
    mock_uow.tests.find_by_id.return_value = None
    service = _make_service(mock_uow, mock_storage)

    with pytest.raises(TestNotFoundError):
        await service.export_test(1)

    mock_uow.artifacts.list_by_test.assert_not_awaited()


@pytest.mark.asyncio
async def test_export_test_not_parsed(mock_uow, mock_storage):
    test = make_test(status=TestStatus.PROCESSING)
    service = _make_service(mock_uow, mock_storage)
    mock_uow.tests.find_by_id.return_value = test

    with pytest.raises(ExportNotAvailableError):
        await service.export_test(test.id)

    mock_uow.artifacts.list_by_test.assert_not_awaited()


@pytest.mark.asyncio
async def test_export_test_skips_missing_artifact(mock_uow, mock_storage):
    test = make_test(status=TestStatus.PARSED, name="mips")
    service = _make_service(mock_uow, mock_storage)
    mock_uow.tests.find_by_id.return_value = test
    mock_uow.artifacts.list_by_test.return_value = [
        _artifact("memin.yaml"),
        _artifact("gone.yaml"),
    ]

    def _load(key):
        if key.endswith("gone.yaml"):
            raise KeyError(key)
        return b"ok"

    mock_storage.load.side_effect = _load

    buffer, _ = await service.export_test(test.id)

    with zipfile.ZipFile(buffer) as zf:
        assert zf.namelist() == ["memin.yaml"]
