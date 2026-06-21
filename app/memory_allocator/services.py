import asyncio
import re
from pathlib import Path

import aiofiles

from app.core.storage import StorageBackend
from app.core.unit_of_work import UnitOfWork
from app.memory_allocator.enums import ArtifactKind, TestStatus
from app.memory_allocator.exceptions import (
    EmptyFileError,
    InvalidUploadError,
    ParsingError,
    PlatformExtractionError,
)
from app.memory_allocator.models import (
    Block,
    Module,
    Partition,
    Platform,
    Region,
    TestArtifact,
    TestCase,
)
from app.memory_allocator.schemas import TestDomain
from app.memory_allocator.utils.parser import parse_yaml
from app.memory_allocator.utils.thread_utils import run_in_thread
from app.users.models import User

PATTERNS = {
    r"memin\.ya?ml": ArtifactKind.CONFIG,
    r"in_amp_configuration\.ya?ml": ArtifactKind.SHARED_GROUPS,
    r"in_[a-zA-Z0-9_]+_constraints\.ya?ml": ArtifactKind.INPUT_CONSTRAINTS,
    r"out_[a-zA-Z0-9_]+_arch_early\.ya?ml": ArtifactKind.OUTPUT_ARCH,
    r"out_[a-zA-Z0-9_]+_vdefinitions\.ya?ml": ArtifactKind.OUTPUT_VDEFINITIONS,
    r"memin\.log": ArtifactKind.LOG,
    r"status\.ya?ml": ArtifactKind.STATUS,
}


class IngestionService:
    def __init__(self, uow: UnitOfWork, storage: StorageBackend):
        self.uow = uow
        self.storage = storage

    async def ingest(self, folder_path: Path, test_name: str, uploaded_by: User) -> TestDomain:
        if not folder_path.is_dir():
            raise InvalidUploadError(test_name, "is not a directory")
        memin_path = folder_path / "memin.yaml"
        if not memin_path.exists():
            raise InvalidUploadError(test_name, "no memory configuration file")

        platform = await self._process_memin(memin_path)

        test = TestCase(name=test_name, platform=platform, uploaded_by=uploaded_by)

        in_block_pattern = r"^.*/in_[a-zA-Z0-9_]+_constraints\.ya?ml$"
        in_block_files = [
            file for file in folder_path.rglob("*")
            if file.is_file() and re.match(in_block_pattern, str(file))
        ]
        try:
            await asyncio.gather(*(self._process_constraints(file=f, test=test)
                                   for f in in_block_files))
        except (KeyError, TypeError, AttributeError) as exc:
            raise ParsingError(repr(exc)) from exc

        self.uow.tests.add(test)
        await self.uow.flush()

        test.module_count = len(test.modules)
        kernel = sum(len(m.kernel_blocks) for m in test.modules)
        partition = sum(len(p.blocks) for m in test.modules for p in m.partitions)
        test.block_count = kernel + partition
        (test.kernel_entry_count,
         test.user_entry_count) = await self._count_output_entries(folder_path)
        test.status = TestStatus.PARSED

        try:
            await self._save_artifacts(test=test, folder_path=folder_path)
            await self.uow.commit()
        except Exception:
            await self.uow.rollback()
            raise
        return TestDomain.model_validate(test)

    async def _process_memin(self, memin_path: Path) -> Platform:
        async with aiofiles.open(memin_path, "rb") as f:
            content = await f.read()
        if not content:
            raise EmptyFileError(str(memin_path.parent.absolute()))
        data = await run_in_thread(parse_yaml, content)
        if "mmu_family" not in data or "memory" not in data or "page_size" not in data["memory"]:
            raise PlatformExtractionError()
        if (not isinstance(data["mmu_family"], str) or
                not isinstance(data["memory"]["page_size"], int)):
            raise PlatformExtractionError()
        platform = await self.uow.platforms.get_or_create(
            mmu_family=data["mmu_family"], page_size=data["memory"]["page_size"], config=data
        )
        return platform

    async def _process_constraints(self, file: Path, test: TestCase) -> None:
        async with aiofiles.open(file, "rb") as f:
            content = await f.read()
            if not content:
                raise EmptyFileError(str(file.absolute()))
        data = await run_in_thread(parse_yaml, content)
        if "module_name" not in data:
            raise InvalidUploadError(str(file.absolute()), "No module_name param")
        address_space_base = data.get("address_space_base")
        module = Module(
            name=data["module_name"],
            address_space_base=address_space_base,
            test=test
        )
        await self._process_module(module=module, data=data)

    async def _process_module(self, module: Module, data: dict) -> None:
        # Kernel memory blocks
        for block_name, block_data in data.get("kernel_memory_blocks", {}).items():
            await self._create_block(
                name=block_name, data=block_data, module=module, partition=None
            )
        # Partitions
        for part in data.get("partitions", []):
            partition = Partition(
                name=part["part_name"],
                space_id=part["space_id"],
                module=module
            )
            for block_name, block_data in part.get("memory_blocks", {}).items():
                await self._create_block(
                    name=block_name, data=block_data, module=None, partition=partition
                )

    async def _create_block(
            self,
            name: str,
            data: dict,
            module: Module | None,
            partition: Partition | None
    ) -> None:
        block = Block(
            name=name,
            access=data["access"],
            align=data["align"],
            cache_policy=data["cache_policy"],
            content_type=data.get("content_type"),
            init_file=data.get("init_file"),
            init_stage=data.get("init_stage"),
            init_type=data.get("init_type"),
            is_contiguous=data["is_contiguous"],
            is_shadow=data["is_shadow"],
            is_system=data["is_system"],
            no_shadow=data["no_shadow"],
            paddr=data.get("paddr"),
            vaddr=data.get("vaddr"),
            size=data.get("size"),
            shadow_offset=data.get("shadow_offset"),
            shadow_scale=data.get("shadow_scale"),
            shadow_type=data.get("shadow_type"),
            safety_zone_before=data["safety_zone_before"],
            safety_zone_before_unmapped=data["safety_zone_before_unmapped"],
            safety_zone_after=data["safety_zone_after"],
            safety_zone_after_unmapped=data["safety_zone_after_unmapped"],
            module=module,
            partition=partition
        )
        for region_data in data.get("regions", []):
            Region(
                paddr=region_data["paddr"],
                size=region_data["size"],
                vaddr=region_data["vaddr"],
                block=block
            )

    async def _count_output_entries(self, folder_path: Path) -> tuple[int, int]:
        out_files = [
            f for f in folder_path.iterdir()
            if f.is_file() and re.match(r"out_[a-zA-Z0-9_]+_arch_early\.ya?ml$", f.name)
        ]
        if not out_files:
            return 0, 0
        out_file = out_files[0]
        try:
            async with aiofiles.open(out_files[0], "rb") as f:
                content = await f.read()
            data = await run_in_thread(parse_yaml, content)
            if not data:
                return 0, 0
            kernel_count = len(data.get("kernel_entries", []))
            map_entries = data.get("user_entries", {}).get("map_entries", [])
            user_count = sum(len(space) for space in map_entries)
        except Exception as exc:
            raise ParsingError(str(out_file)) from exc
        return kernel_count, user_count

    def _match_kind(self, filename: Path) -> ArtifactKind | None:
        for pattern, artifact_kind in PATTERNS.items():
            if re.match(pattern, str(filename.name)):
                return artifact_kind
        return None

    async def _save_artifacts(self, test: TestCase, folder_path: Path) -> None:
        saved_keys: list[str] = []
        try:
            for filename in folder_path.iterdir():
                kind = self._match_kind(filename)
                if not kind:
                    continue
                storage_key = f"{test.id}/{filename.name}"
                async with aiofiles.open(filename, "rb") as f:
                    content = await f.read()
                await self.storage.save(storage_key, content)
                saved_keys.append(storage_key)
                artifact = TestArtifact(
                    kind=kind,
                    filename=filename.name,
                    storage_key=storage_key,
                    test=test
                )
                self.uow.artifacts.add(artifact)
        except Exception:
            for key in saved_keys:
                await self.storage.delete(key)
            raise


class TestcaseService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def list_all(self) -> list[TestDomain]:
        tests = await self.uow.tests.list_all()
        return [TestDomain.model_validate(test) for test in tests]
