from datetime import UTC, datetime, timedelta
from unittest.mock import Mock

import pytest

from app.memory_allocator.enums import TestStatus, ValidationStatus
from app.memory_allocator.services import SweeperService
from tests.factories import (
    make_platform,
    make_test,
    make_user,
    make_validation_result,
)

STALE_AFTER = timedelta(minutes=30)


async def _seed_validations(uow, rows: list[tuple[ValidationStatus, timedelta]]) -> list[int]:
    test_id, = await _seed(uow, [(TestStatus.PARSED, timedelta(hours=5))])
    test = await uow.tests.find_by_id(test_id)
    now = datetime.now(UTC)
    ids = []
    for status, age in rows:
        validation = make_validation_result(
            id=None,
            test=test,
            status=status,
            requested_at=now - age,
            checked_at=None,
        )
        uow.validations.add(validation)
        await uow.commit()
        await uow.refresh(validation)
        ids.append(validation.id)
    return ids


async def _seed(uow, rows: list[tuple[TestStatus, timedelta]]) -> list[int]:
    user = make_user()
    platform = make_platform(id=None)
    uow.users.add(user)
    uow.platforms.add(platform)
    await uow.commit()

    now = datetime.now(UTC)
    ids = []
    for status, age in rows:
        test = make_test(
            id=None,
            status=status,
            uploaded_at=now - age,
            platform=platform,
            uploaded_by=user,
        )
        uow.tests.add(test)
        await uow.commit()
        await uow.refresh(test)
        ids.append(test.id)
    return ids


@pytest.mark.asyncio(loop_scope="session")
async def test_sweeper_requeues_only_stale_pending(alembic_uow):
    fresh_pending, stale_pending, *_ = await _seed(alembic_uow, [
        (TestStatus.PENDING, timedelta(seconds=0)),
        (TestStatus.PENDING, timedelta(hours=1)),
        (TestStatus.PROCESSING, timedelta(hours=1)),
        (TestStatus.PARSED, timedelta(hours=1)),
        (TestStatus.ERROR, timedelta(hours=1)),
    ])

    requeued_ids = []
    service = SweeperService(alembic_uow, requeued_ids.append, Mock())
    count = await service.requeue_stale_pending(STALE_AFTER, limit=100)

    assert requeued_ids == [stale_pending]
    assert count == 1
    assert fresh_pending not in requeued_ids


@pytest.mark.asyncio(loop_scope="session")
async def test_sweeper_takes_oldest_first_within_limit(alembic_uow):
    oldest, middle, newest = await _seed(alembic_uow, [
        (TestStatus.PENDING, timedelta(hours=3)),
        (TestStatus.PENDING, timedelta(hours=2)),
        (TestStatus.PENDING, timedelta(hours=1)),
    ])

    requeued_ids = []
    service = SweeperService(alembic_uow, requeued_ids.append, Mock())
    count = await service.requeue_stale_pending(STALE_AFTER, limit=2)

    assert requeued_ids == [oldest, middle]
    assert count == 2
    assert newest not in requeued_ids


@pytest.mark.asyncio(loop_scope="session")
async def test_sweeper_requeues_only_stale_pending_validations(alembic_uow):
    fresh_pending, stale_pending, *_ = await _seed_validations(alembic_uow, [
        (ValidationStatus.PENDING, timedelta(seconds=0)),
        (ValidationStatus.PENDING, timedelta(hours=1)),
        (ValidationStatus.RUNNING, timedelta(hours=1)),
        (ValidationStatus.COMPLETED, timedelta(hours=1)),
        (ValidationStatus.FAILED, timedelta(hours=1)),
    ])

    requeued_ids = []
    tests_dispatch = Mock()
    service = SweeperService(alembic_uow, tests_dispatch, requeued_ids.append)
    count = await service.requeue_stale_validations(STALE_AFTER, limit=100)

    assert requeued_ids == [stale_pending]
    assert count == 1
    assert fresh_pending not in requeued_ids
    tests_dispatch.assert_not_called()
