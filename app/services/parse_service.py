from typing import List
from pathlib import Path
import aiofiles
import asyncio

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.file_utils import detect_file_type
from app.core.enums import InputType
from app.core.parser import parse_yaml, parse_json
from app.core.thread_utils import run_in_thread
from app.models.memory_allocator import TestCase, Module, Block, Partition, Region


async def process_folder(folder_path: str, db: AsyncSession) -> List[int]:
    """
    Iterate through all files in the given folder and process them.

    :param folder_path: Path to the folder containing files to process.
    :param db: Database session.
    :return: Indices of processed files.
    """
    path = Path(folder_path)

    if not path.is_dir():
        raise ValueError(f"The provided path '{folder_path}' is not a directory.")

    test = TestCase(name=path.name)
    db.add(test)
    await db.flush()

    files = [file for file in path.rglob("*") if file.is_file()]
    module_ids = await asyncio.gather(*(process_file(file=f, db=db, test=test) for f in files))

    return module_ids


async def process_file(file: Path, db: AsyncSession, test: TestCase) -> int:
    """
    Process a single file and save its data to the database.

    :param file: Path to the file.
    :param db: Database session.
    :param test: TestCase instance to associate the data with.
    :return: ID of the file entry in the database.
    """
    async with aiofiles.open(file, "rb") as f:
        content = await f.read()
        if not content or len(content) == 0:
            raise HTTPException(status_code=400, detail="Empty file.")

        filetype = detect_file_type(file.name)

        match filetype:
            case InputType.YAML:
                data = await run_in_thread(parse_yaml, content)
            case InputType.JSON:
                data = await run_in_thread(parse_json, content)
            case _:
                raise HTTPException(status_code=400, detail="Unsupported file type")

        module_name = data.get("module_name", "default_module")
        address_space_base = data.get("address_space_base")
        module = Module(name=module_name, address_space_base=address_space_base, test_id=test.id)
        db.add(module)
        await db.flush()
        await process_module(module=module, data=data, db=db)
        await db.flush()
        return module.id


async def process_module(module: Module, data: dict, db: AsyncSession) -> None:
    """
    Process a module's data and save it to the database.

    :param module: Module instance to populate.
    :param data: Processed data dictionary.
    :param db: Database session.
    """
    # Kernel memory blocks
    for block_name, block_data in data.get("kernel_memory_blocks", {}).items():
        await create_block(
            block_name, block_data, module_id=module.id, partition_id=None, db=db
        )
    # Partitions
    for part in data.get("partitions", []):
        partition = Partition(
            name=part["part_name"],
            space_id=part["space_id"],
            module_id=module.id
        )
        db.add(partition)
        await db.flush()

        for block_name, block_data in part.get("memory_blocks", {}).items():
            await create_block(
                block_name, block_data, module_id=module.id, partition_id=partition.id, db=db
            )


async def create_block(block_name: str, block_data: dict,
                       module_id: int, partition_id: int | None, db: AsyncSession
                       ) -> None:
    """
    Create a Block and its associated Regions in the database.

    :param block_name: Name of the block.
    :param block_data: Data dictionary for the block.
    :param module_id: ID of the associated Module.
    :param partition_id: ID of the associated Partition.
    :param db: Database session.
    """
    block = Block(
        name=block_name,
        access=block_data["access"],
        align=block_data["align"],
        cache_policy=block_data["cache_policy"],
        content_type=block_data.get("content_type"),
        init_file=block_data.get("init_file"),
        init_stage=block_data.get("init_stage"),
        init_type=block_data.get("init_type"),
        is_contiguous=block_data["is_contiguous"],
        is_shadow=block_data["is_shadow"],
        is_shareable=block_data["is_shareable"],
        is_system=block_data["is_system"],
        no_shadow=block_data["no_shadow"],
        paddr=block_data.get("paddr"),
        vaddr=block_data["vaddr"],
        size=block_data.get("size"),
        shadow_offset=block_data.get("shadow_offset"),
        shadow_scale=block_data.get("shadow_scale"),
        shadow_type=block_data.get("shadow_type"),
        safety_zone_before=block_data["safety_zone_before"],
        safety_zone_before_unmapped=block_data["safety_zone_before_unmapped"],
        safety_zone_after=block_data["safety_zone_after"],
        safety_zone_after_unmapped=block_data["safety_zone_after_unmapped"],
        module_id=module_id,
        partition_id=partition_id
    )
    db.add(block)
    await db.flush()
    for region_data in block_data.get("regions", []):
        region = Region(
            paddr=region_data["paddr"],
            size=region_data["size"],
            vaddr=region_data["vaddr"],
            block_id=block.id
        )
        db.add(region)
