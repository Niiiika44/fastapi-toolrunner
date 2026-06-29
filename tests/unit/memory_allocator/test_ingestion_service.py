import datetime
import io
from unittest.mock import Mock

import pytest
from fastapi import UploadFile

from app.memory_allocator.exceptions import (
    EmptyFileError,
    InvalidUploadError,
    ParsingError,
    PlatformExtractionError,
)
from app.memory_allocator.models import Platform
from app.memory_allocator.schemas import TestDomain
from app.memory_allocator.services import IngestionService
from tests.conftest import make_zip
from tests.factories import make_test, make_user


def _simulate_persist(test):
    """Mimic DB-assigned fields on flush."""
    if test.id is None:
        test.id = 1
    if test.uploaded_at is None:
        test.uploaded_at = datetime.datetime.now(datetime.UTC)
    for attr in ("module_count", "block_count", "kernel_entry_count", "user_entry_count"):
        if getattr(test, attr) is None:
            setattr(test, attr, 0)


def _zip_upload(folder, filename="real_test.zip") -> UploadFile:
    """Wrap a folder's contents into a zip UploadFile."""
    return UploadFile(file=io.BytesIO(make_zip(folder)), filename=filename)


def _make_service(mock_uow, mock_storage, dispatch=None):
    return IngestionService(mock_uow, mock_storage, enqueue_processing=dispatch or Mock())


@pytest.mark.asyncio
async def test_accept_upload_not_a_zip(mock_uow, mock_storage):
    service = _make_service(mock_uow, mock_storage)
    file = UploadFile(file=io.BytesIO(b"not a zip"), filename="data.txt")
    with pytest.raises(InvalidUploadError):
        await service.accept_upload(file=file, uploaded_by=make_user())
    service.enqueue_processing.assert_not_called()
    mock_uow.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_accept_upload_error_memin(mock_uow, mock_storage, example_correct_folder):
    (example_correct_folder / "memin.yaml").write_text(".abc")
    service = _make_service(mock_uow, mock_storage)
    with pytest.raises(PlatformExtractionError):
        await service.accept_upload(
            file=_zip_upload(example_correct_folder),
            uploaded_by=make_user()
        )


@pytest.mark.asyncio
async def test_accept_upload_no_memin_file(mock_uow, mock_storage, tmp_path):
    service = _make_service(mock_uow, mock_storage)
    with pytest.raises(InvalidUploadError):
        await service.accept_upload(file=_zip_upload(tmp_path), uploaded_by=make_user())


@pytest.mark.asyncio
async def test_accept_upload_no_content(mock_uow, mock_storage, tmp_path):
    (tmp_path / "memin.yaml").write_text("")
    service = _make_service(mock_uow, mock_storage)
    with pytest.raises(EmptyFileError):
        await service.accept_upload(file=_zip_upload(tmp_path), uploaded_by=make_user())


@pytest.mark.asyncio
@pytest.mark.parametrize("memin_content", [
    "memory:\n  page_size: 0x1000\n",
    "mmu_family: mips_r6000\n",
    "mmu_family: 123\nmemory:\n  page_size: 0x1000\n",
    "mmu_family: mips_r6000\nmemory:\n  page_size: string\n",
])
async def test_accept_upload_memin_bad_content(mock_uow, mock_storage, tmp_path, memin_content):
    (tmp_path / "memin.yaml").write_text(memin_content)
    service = _make_service(mock_uow, mock_storage)
    with pytest.raises(PlatformExtractionError):
        await service.accept_upload(file=_zip_upload(tmp_path), uploaded_by=make_user())


@pytest.mark.asyncio
async def test_accept_upload_success(mock_uow, mock_storage, example_correct_folder):
    dispatch = Mock()
    service = _make_service(mock_uow, mock_storage, dispatch)
    mock_uow.tests.add.side_effect = _simulate_persist
    mock_uow.platforms.get_or_create.return_value = Platform(
        id=1, mmu_family="mips_r6000", page_size=4096
    )

    result = await service.accept_upload(
        file=_zip_upload(example_correct_folder),
        uploaded_by=make_user()
    )

    orm_test = mock_uow.tests.add.call_args.args[0]
    assert mock_storage.save.await_args.args[0] == f"uploads/{orm_test.id}.zip"
    assert isinstance(result, TestDomain)
    assert result.name == "real_test"
    assert result.status == "pending"
    mock_uow.commit.assert_awaited_once()
    dispatch.assert_called_once_with(orm_test.id)


@pytest.mark.asyncio
async def test_accept_enqueue_after_commit(mock_uow, mock_storage, example_correct_folder):
    mock_uow.platforms.get_or_create.return_value = Platform(
        id=1, mmu_family="mips_r6000", page_size=4096
    )
    mock_uow.tests.add.side_effect = _simulate_persist

    def _assert_committed(_):
        assert mock_uow.commit.await_count == 1

    dispatch = Mock(side_effect=_assert_committed)
    service = _make_service(mock_uow, mock_storage, dispatch)

    await service.accept_upload(_zip_upload(example_correct_folder), make_user())

    dispatch.assert_called_once()


@pytest.mark.asyncio
async def test_process_upload_success(mock_uow, mock_storage, example_correct_folder):
    service = _make_service(mock_uow, mock_storage)
    mock_uow.tests.add.side_effect = _simulate_persist
    test = make_test(id=1)
    content = make_zip(example_correct_folder)
    result = await service.process_upload(test=test, content=content)

    assert result is None

    assert test.status == "parsed"
    assert test.kernel_entry_count == 2
    assert test.user_entry_count == 6
    assert test.module_count == 1
    assert test.block_count == 72
    assert len(test.modules) == 1
    module = test.modules[0]
    assert module.kernel_blocks or module.partitions

    assert len(test.artifacts) == 7
    assert mock_storage.save.await_count == 7

    saved_keys = [call.args[0] for call in mock_storage.save.await_args_list]
    assert all(key.startswith(f"artifacts/{test.id}/") for key in saved_keys)
    assert {key.split("/")[-1] for key in saved_keys} == {
        "memin.yaml",
        "in_amp_configuration.yaml",
        "in_single_constraints.yaml",
        "out_single_arch_early.yaml",
        "out_single_vdefinitions.yaml",
        "memin.log",
        "status.yaml",
    }
    mock_uow.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_process_upload_delete_orphan_children(
    mock_uow, mock_storage, example_correct_folder
):
    mock_storage.save.side_effect = [None, None, RuntimeError("full disk")]
    service = _make_service(mock_uow, mock_storage)
    test = make_test(id=1)
    content = make_zip(example_correct_folder)
    with pytest.raises(RuntimeError):
        await service.process_upload(test=test, content=content)
    mock_uow.rollback.assert_awaited_once()
    assert mock_storage.delete.await_count == 2


@pytest.mark.asyncio
async def test_process_upload_no_output(mock_uow, mock_storage, example_correct_folder):
    (example_correct_folder / "out_single_arch_early.yaml").unlink()
    (example_correct_folder / "out_single_vdefinitions.yaml").unlink()
    service = _make_service(mock_uow, mock_storage)
    mock_uow.tests.add.side_effect = _simulate_persist
    test = make_test(id=1)
    content = make_zip(example_correct_folder)
    await service.process_upload(test=test, content=content)
    mock_uow.commit.assert_awaited_once()
    assert test.kernel_entry_count == 0
    assert test.user_entry_count == 0


@pytest.mark.asyncio
async def test_process_upload_error_output(mock_uow, mock_storage, example_correct_folder):
    (example_correct_folder / 'out_single_arch_early.yaml').write_text("{ broken: ][ yaml")
    service = _make_service(mock_uow, mock_storage)
    mock_uow.tests.add.side_effect = _simulate_persist
    test = make_test(id=1)
    content = make_zip(example_correct_folder)
    with pytest.raises(ParsingError):
        await service.process_upload(test=test, content=content)


@pytest.mark.parametrize("filename", [
    "memin.log",
    "out_single_arch_early.yaml",
    "status.yaml",
    "out_single_vdefinitions.yaml"
])
@pytest.mark.asyncio
async def test_process_upload_empty_file(mock_uow, mock_storage, example_correct_folder, filename):
    (example_correct_folder / filename).write_text("")
    service = _make_service(mock_uow, mock_storage)
    test = make_test(id=1)
    content = make_zip(example_correct_folder)
    mock_uow.tests.add.side_effect = _simulate_persist
    await service.process_upload(test=test, content=content)
    mock_uow.commit.assert_awaited_once()
