import datetime
import io

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
from tests.factories import make_user


def _simulate_persist(test):
    """Mimic DB-assigned fields on flush."""
    if test.id is None:
        test.id = 1
    if test.uploaded_at is None:
        test.uploaded_at = datetime.datetime.now(datetime.UTC)


def _zip_upload(folder, filename="real_test.zip") -> UploadFile:
    """Wrap a folder's contents into a zip UploadFile."""
    return UploadFile(file=io.BytesIO(make_zip(folder)), filename=filename)


@pytest.mark.asyncio
async def test_ingestion_not_a_zip(mock_uow, mock_storage):
    service = IngestionService(mock_uow, mock_storage)
    file = UploadFile(file=io.BytesIO(b"not a zip"), filename="data.txt")
    with pytest.raises(InvalidUploadError):
        await service.ingest(file=file, uploaded_by=make_user())


@pytest.mark.asyncio
async def test_ingestion_no_memin_file(mock_uow, mock_storage, tmp_path):
    service = IngestionService(mock_uow, mock_storage)
    with pytest.raises(InvalidUploadError):
        await service.ingest(file=_zip_upload(tmp_path), uploaded_by=make_user())


@pytest.mark.asyncio
async def test_memin_no_content(mock_uow, mock_storage, tmp_path):
    (tmp_path / "memin.yaml").write_text("")
    service = IngestionService(mock_uow, mock_storage)
    with pytest.raises(EmptyFileError):
        await service.ingest(file=_zip_upload(tmp_path), uploaded_by=make_user())


@pytest.mark.asyncio
@pytest.mark.parametrize("memin_content", [
    "memory:\n  page_size: 0x1000\n",
    "mmu_family: mips_r6000\n",
    "mmu_family: 123\nmemory:\n  page_size: 0x1000\n",
    "mmu_family: mips_r6000\nmemory:\n  page_size: string\n",
])
async def test_memin_bad_content(mock_uow, mock_storage, tmp_path, memin_content):
    (tmp_path / "memin.yaml").write_text(memin_content)
    service = IngestionService(mock_uow, mock_storage)
    with pytest.raises(PlatformExtractionError):
        await service.ingest(file=_zip_upload(tmp_path), uploaded_by=make_user())


@pytest.mark.asyncio
async def test_ingestion_success(mock_uow, mock_storage, example_correct_folder):
    service = IngestionService(mock_uow, mock_storage)
    mock_uow.tests.add.side_effect = _simulate_persist
    mock_uow.platforms.get_or_create.return_value = Platform(
        id=1, mmu_family="mips_r6000", page_size=4096
    )

    result = await service.ingest(
        file=_zip_upload(example_correct_folder),
        uploaded_by=make_user()
    )

    orm_test = mock_uow.tests.add.call_args.args[0]
    assert len(orm_test.modules) == 1
    module = orm_test.modules[0]
    assert module.kernel_blocks or module.partitions
    assert len(orm_test.artifacts) == 7
    assert mock_storage.save.call_count == 7

    saved_keys = [call.args[0].split("/")[-1] for call in mock_storage.save.await_args_list]
    assert set(saved_keys) == {
        "in_amp_configuration.yaml",
        "in_single_constraints.yaml",
        "memin.log",
        "out_single_arch_early.yaml",
        "out_single_vdefinitions.yaml",
        "status.yaml",
        "memin.yaml"
    }

    assert isinstance(result, TestDomain)
    assert result.name == "real_test"
    assert result.module_count == 1
    assert result.block_count == 72
    assert result.status == "parsed"
    assert result.kernel_entry_count == 2
    assert result.user_entry_count == 6
    mock_uow.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_ingestion_delete_orphan_children(mock_uow, mock_storage, example_correct_folder):
    mock_storage.save.side_effect = [None, None, RuntimeError("full disk")]
    service = IngestionService(mock_uow, mock_storage)
    with pytest.raises(RuntimeError):
        await service.ingest(
            file=_zip_upload(example_correct_folder),
            uploaded_by=make_user()
        )
    mock_uow.rollback.assert_awaited_once()
    assert mock_storage.delete.await_count == 2


@pytest.mark.asyncio
async def test_ingestion_no_output(mock_uow, mock_storage, example_correct_folder):
    (example_correct_folder / "out_single_arch_early.yaml").unlink()
    (example_correct_folder / "out_single_vdefinitions.yaml").unlink()
    service = IngestionService(mock_uow, mock_storage)
    mock_uow.tests.add.side_effect = _simulate_persist
    mock_uow.platforms.get_or_create.return_value = Platform(
        id=1, mmu_family="mips_r6000", page_size=4096
    )
    test = await service.ingest(
        file=_zip_upload(example_correct_folder),
        uploaded_by=make_user()
    )
    mock_uow.commit.assert_awaited_once()
    assert test.kernel_entry_count == 0
    assert test.user_entry_count == 0


@pytest.mark.asyncio
async def test_ingestion_error_memin(mock_uow, mock_storage, example_correct_folder):
    (example_correct_folder / "memin.yaml").write_text(".abc")
    service = IngestionService(mock_uow, mock_storage)
    with pytest.raises(PlatformExtractionError):
        await service.ingest(
            file=_zip_upload(example_correct_folder),
            uploaded_by=make_user()
        )


@pytest.mark.asyncio
async def test_ingestion_error_output(mock_uow, mock_storage, example_correct_folder):
    (example_correct_folder / 'out_single_arch_early.yaml').write_text("{ broken: ][ yaml")
    service = IngestionService(mock_uow, mock_storage)
    with pytest.raises(ParsingError):
        await service.ingest(
            file=_zip_upload(example_correct_folder),
            uploaded_by=make_user()
        )


@pytest.mark.parametrize("filename", [
    "memin.log",
    "out_single_arch_early.yaml",
    "status.yaml",
    "out_single_vdefinitions.yaml"
])
@pytest.mark.asyncio
async def test_ingestion_empty_file(mock_uow, mock_storage, example_correct_folder, filename):
    (example_correct_folder / filename).write_text("")
    service = IngestionService(mock_uow, mock_storage)
    mock_uow.tests.add.side_effect = _simulate_persist
    mock_uow.platforms.get_or_create.return_value = Platform(
        id=1, mmu_family="mips_r6000", page_size=4096
    )
    await service.ingest(
        file=_zip_upload(example_correct_folder),
        uploaded_by=make_user()
    )
    mock_uow.commit.assert_awaited_once()
