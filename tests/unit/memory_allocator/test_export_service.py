import logging
import zipfile
from unittest.mock import Mock

import pytest

from app.memory_allocator.enums import TestStatus
from app.memory_allocator.exceptions import (
    ArtifactNotFoundError,
    ExportNotAvailableError,
    StorageKeyNotFoundError,
    TestNotFoundError,
)
from app.memory_allocator.schemas import ArtifactContentDomain, ArtifactLinkDomain
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


PRESIGNED_URL = "http://localhost:9011/autorunning/artifacts/1/memin.yaml?X-Amz-Signature=deadbeef"


def _own_artifact(artifact_id: int = 1, test_id: int = 1) -> Mock:
    return Mock(
        id=artifact_id,
        test_id=test_id,
        filename="memin.yaml",
        storage_key=f"artifacts/{test_id}/memin.yaml",
    )


@pytest.mark.asyncio
async def test_artifact_download_returns_link_when_storage_supports_it(mock_uow, mock_storage):
    service = _make_service(mock_uow, mock_storage)
    mock_uow.artifacts.find_by_id.return_value = _own_artifact()
    mock_storage.exists.return_value = True
    mock_storage.presigned_url.return_value = PRESIGNED_URL

    artifact = await service.artifact_download(test_id=1, artifact_id=1)

    assert isinstance(artifact, ArtifactLinkDomain)
    assert artifact.url == PRESIGNED_URL
    assert artifact.filename == "memin.yaml"
    mock_storage.load.assert_not_awaited()


@pytest.mark.asyncio
async def test_artifact_download_returns_content_without_presigned(mock_uow, mock_storage):
    service = _make_service(mock_uow, mock_storage)
    mock_uow.artifacts.find_by_id.return_value = _own_artifact()
    mock_storage.exists.return_value = True
    mock_storage.presigned_url.return_value = None
    mock_storage.load.return_value = b"file-bytes"

    artifact = await service.artifact_download(test_id=1, artifact_id=1)

    assert isinstance(artifact, ArtifactContentDomain)
    assert artifact.content == b"file-bytes"
    assert artifact.filename == "memin.yaml"


@pytest.mark.asyncio
async def test_artifact_download_rejects_artifact_of_another_test(mock_uow, mock_storage):
    service = _make_service(mock_uow, mock_storage)
    mock_uow.artifacts.find_by_id.return_value = _own_artifact(artifact_id=7, test_id=99)

    with pytest.raises(ArtifactNotFoundError):
        await service.artifact_download(test_id=1, artifact_id=7)

    mock_storage.presigned_url.assert_not_awaited()
    mock_storage.load.assert_not_awaited()


@pytest.mark.asyncio
async def test_artifact_download_raises_when_artifact_is_missing(mock_uow, mock_storage):
    service = _make_service(mock_uow, mock_storage)
    mock_uow.artifacts.find_by_id.return_value = None

    with pytest.raises(ArtifactNotFoundError):
        await service.artifact_download(test_id=1, artifact_id=1)

    mock_storage.exists.assert_not_awaited()


@pytest.mark.asyncio
async def test_artifact_download_raises_when_object_is_missing(mock_uow, mock_storage):
    service = _make_service(mock_uow, mock_storage)
    mock_uow.artifacts.find_by_id.return_value = _own_artifact()
    mock_storage.exists.return_value = False

    with pytest.raises(StorageKeyNotFoundError):
        await service.artifact_download(test_id=1, artifact_id=1)

    mock_storage.presigned_url.assert_not_awaited()


@pytest.mark.asyncio
async def test_artifact_download_does_not_log_the_url(mock_uow, mock_storage, caplog):
    service = _make_service(mock_uow, mock_storage)
    mock_uow.artifacts.find_by_id.return_value = _own_artifact()
    mock_storage.exists.return_value = True
    mock_storage.presigned_url.return_value = PRESIGNED_URL

    with caplog.at_level(logging.INFO):
        await service.artifact_download(test_id=1, artifact_id=1)

    requested = [r for r in caplog.records if r.getMessage() == "artifact.download_requested"]
    assert len(requested) == 1
    assert requested[0].artifact_id == 1
    logged_values = [str(value) for value in vars(requested[0]).values()]
    assert not any("X-Amz-Signature" in value for value in logged_values)
