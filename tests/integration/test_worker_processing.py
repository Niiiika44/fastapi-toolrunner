import io

import pytest
from fastapi import UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.storage import LocalStorage
from app.core.unit_of_work import UnitOfWork
from app.memory_allocator.enums import TestStatus
from app.memory_allocator.models import Block, Module, Partition
from app.memory_allocator.services import IngestionService
from app.memory_allocator.tasks import tasks_testcase
from app.users.enums import UserJobTitle
from app.users.models import User
from tests.conftest import fake_uow, make_zip


@pytest.mark.asyncio(loop_scope="session")
async def test_worker_parses_real_zip(
    engine_alembic,
    alembic_uow,
    example_correct_folder,
    tmp_path,
    monkeypatch,
):
    storage = LocalStorage(tmp_path)
    uow = alembic_uow

    user = User(
        username="worker-user",
        email="worker@ispras.ru",
        password="x",
        first_name="Worker",
        last_name="User",
        job_title=UserJobTitle.DEVELOPER,
    )
    uow.users.add(user)
    await uow.commit()
    await uow.refresh(user)

    zip_bytes = make_zip(example_correct_folder)
    upload = UploadFile(filename="testcase.zip", file=io.BytesIO(zip_bytes))
    ingestion = IngestionService(uow, storage, enqueue_processing=lambda _: None)
    request = await ingestion.accept_upload(upload, user)

    monkeypatch.setattr(tasks_testcase, "build_uow", lambda: fake_uow(engine_alembic))
    monkeypatch.setattr(tasks_testcase, "get_storage", lambda: storage)
    await tasks_testcase._process_test(request.id)

    async with AsyncSession(engine_alembic, expire_on_commit=False) as session:
        test = await UnitOfWork(session).tests.find_for_processing(request.id)
        assert test.status == TestStatus.PARSED
        assert test.module_count == 1
        assert test.block_count == 72

        modules = (await session.execute(select(func.count()).select_from(Module))).scalar()
        partitions = (await session.execute(select(func.count()).select_from(Partition))).scalar()
        blocks = (await session.execute(select(func.count()).select_from(Block))).scalar()
        assert modules == 1
        assert partitions == 2
        assert blocks == 72
