import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.unit_of_work import UnitOfWork
from app.memory_allocator.checker import MockChecker
from app.memory_allocator.enums import ValidationStatus
from app.memory_allocator.tasks import tasks_validation
from tests.conftest import fake_uow
from tests.factories import make_validation_result


@pytest.mark.asyncio(loop_scope="session")
async def test_worker_validation(
    engine_alembic,
    alembic_uow,
    monkeypatch,
):
    uow = alembic_uow
    checker = MockChecker(0)
    vr = make_validation_result(checked_at=None, checker_version=None)
    uow.validations.add(vr)
    await uow.commit()
    await uow.refresh(vr)

    monkeypatch.setattr(tasks_validation, "build_uow", lambda: fake_uow(engine_alembic))
    monkeypatch.setattr(tasks_validation, "get_checker", lambda: checker)
    await tasks_validation._process_validation(vr.id)

    async with AsyncSession(engine_alembic, expire_on_commit=False) as session:
        validation = await UnitOfWork(session).validations.find_by_id(vr.id)
        assert validation.status == ValidationStatus.COMPLETED
        assert validation.valid is True
        assert validation.schema_valid is True
        assert validation.errors == []
        assert validation.checker_version == "mock-1.0"
        assert validation.checked_at is not None
