import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.unit_of_work import UnitOfWork
from app.memory_allocator.enums import TestStatus
from app.memory_allocator.models import DeadLetter
from app.memory_allocator.services import DeadLetterService
from tests.factories import make_message, make_platform, make_test, make_user


async def _seed_test(uow, status: TestStatus) -> int:
    user = make_user()
    platform = make_platform(id=None)
    uow.users.add(user)
    uow.platforms.add(platform)
    await uow.commit()

    test = make_test(id=None, status=status, platform=platform, uploaded_by=user)
    uow.tests.add(test)
    await uow.commit()
    await uow.refresh(test)
    return test.id


@pytest.mark.asyncio(loop_scope="session")
async def test_dead_letter_closes_hanging_test(engine_alembic, alembic_uow):
    test_id = await _seed_test(alembic_uow, TestStatus.PROCESSING)
    message = make_message(task_name="memory_allocator.process_test", args=[test_id])

    letter_id = await DeadLetterService(alembic_uow).record(message)

    async with AsyncSession(engine_alembic, expire_on_commit=False) as session:
        letters = (await session.execute(select(DeadLetter))).scalars().all()
        test = await UnitOfWork(session).tests.find_by_id(test_id)

    assert [letter.id for letter in letters] == [letter_id]
    assert letters[0].task_name == message.task_name
    assert letters[0].reason == message.reason
    assert letters[0].args == [test_id]
    assert test.status == TestStatus.ERROR
    assert message.reason in test.error_message


@pytest.mark.asyncio(loop_scope="session")
async def test_dead_letter_of_unknown_task_touches_nothing(engine_alembic, alembic_uow):
    test_id = await _seed_test(alembic_uow, TestStatus.PROCESSING)
    message = make_message(task_name="memory_allocator.debug_kill", args=[test_id])

    await DeadLetterService(alembic_uow).record(message)

    async with AsyncSession(engine_alembic, expire_on_commit=False) as session:
        letters_count = (
            await session.execute(select(func.count()).select_from(DeadLetter))
        ).scalar()
        test = await UnitOfWork(session).tests.find_by_id(test_id)

    assert letters_count == 1
    assert test.status == TestStatus.PROCESSING
    assert test.error_message is None


@pytest.mark.asyncio(loop_scope="session")
async def test_dead_letter_keeps_parsed_test_untouched(engine_alembic, alembic_uow):
    test_id = await _seed_test(alembic_uow, TestStatus.PARSED)
    message = make_message(task_name="memory_allocator.process_test", args=[test_id])

    await DeadLetterService(alembic_uow).record(message)

    async with AsyncSession(engine_alembic, expire_on_commit=False) as session:
        letters_count = (
            await session.execute(select(func.count()).select_from(DeadLetter))
        ).scalar()
        test = await UnitOfWork(session).tests.find_by_id(test_id)

    assert letters_count == 1
    assert test.status == TestStatus.PARSED
    assert test.error_message is None
