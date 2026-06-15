from pathlib import Path

import pytest

from app.memory_allocator.exceptions import (
    EmptyFileError,
    InvalidUploadError,
    ParsingError,
    PlatformExtractionError,
)
from app.memory_allocator.models import Platform
from app.memory_allocator.services import IngestionService


@pytest.mark.asyncio
async def test_ingestion_not_a_folder(mock_uow, mock_storage):
    service = IngestionService(mock_uow, mock_storage)
    with pytest.raises(InvalidUploadError):
        await service.ingest(Path("not_a_directory"), "random_name")


@pytest.mark.asyncio
async def test_ingestion_no_memin_file(mock_uow, mock_storage, tmp_path):
    service = IngestionService(mock_uow, mock_storage)
    with pytest.raises(InvalidUploadError):
        await service.ingest(tmp_path, "random_name")


@pytest.mark.asyncio
async def test_memin_no_content(mock_uow, mock_storage, tmp_path):
    (tmp_path / "memin.yaml").write_text("")
    service = IngestionService(mock_uow, mock_storage)
    with pytest.raises(EmptyFileError):
        await service.ingest(tmp_path, "t")


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
        await service.ingest(tmp_path, "t")


@pytest.mark.asyncio
async def test_ingestion_success(mock_uow, mock_storage, example_correct_folder):
    service = IngestionService(mock_uow, mock_storage)
    mock_uow.platforms.get_or_create.return_value = Platform(
        id=1, mmu_family="mips_r6000", page_size=4096
    )

    test = await service.ingest(example_correct_folder, "real_test")

    assert test.name == "real_test"
    assert len(test.modules) == 1
    module = test.modules[0]
    assert module.kernel_blocks or module.partitions
    assert len(test.artifacts) == 7
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
    assert test.module_count == 1
    assert test.block_count == 72
    assert test.status == "parsed"
    assert test.kernel_entry_count == 2
    assert test.user_entry_count == 6
    mock_uow.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_ingestion_delete_orphan_children(mock_uow, mock_storage, example_correct_folder):
    mock_storage.save.side_effect = [None, None, RuntimeError("full disk")]
    service = IngestionService(mock_uow, mock_storage)
    with pytest.raises(RuntimeError):
        await service.ingest(example_correct_folder, "real_test")
    mock_uow.rollback.assert_awaited_once()
    assert mock_storage.delete.await_count == 2


@pytest.mark.asyncio
async def test_ingestion_no_output(mock_uow, mock_storage, example_correct_folder):
    (example_correct_folder / "out_single_arch_early.yaml").unlink()
    (example_correct_folder / "out_single_vdefinitions.yaml").unlink()
    service = IngestionService(mock_uow, mock_storage)
    test = await service.ingest(example_correct_folder, "real_test")
    mock_uow.commit.assert_awaited_once()
    assert test.kernel_entry_count == 0
    assert test.user_entry_count == 0


@pytest.mark.asyncio
async def test_ingestion_error_memin(mock_uow, mock_storage, example_correct_folder):
    (example_correct_folder / "memin.yaml").write_text(".abc")
    service = IngestionService(mock_uow, mock_storage)
    with pytest.raises(PlatformExtractionError):
        await service.ingest(example_correct_folder, "real_test")


@pytest.mark.asyncio
async def test_ingestion_error_output(mock_uow, mock_storage, example_correct_folder):
    (example_correct_folder / 'out_single_arch_early.yaml').write_text("{ broken: ][ yaml")
    service = IngestionService(mock_uow, mock_storage)
    with pytest.raises(ParsingError):
        await service.ingest(example_correct_folder, "real_test")


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
    await service.ingest(example_correct_folder, "real_test")
    mock_uow.commit.assert_awaited_once()
