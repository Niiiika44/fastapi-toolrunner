import pytest
from sqlalchemy import inspect, select

from app.auth.enums import Permission
from app.users.models import User, UserPermission
from app.users.repositories import UserRepository


def loaded(user: User) -> bool:
    return "permissions" not in inspect(user).unloaded


@pytest.mark.asyncio(loop_scope="session")
async def test_find_by_id_loads_permissions(db_session, create_test_user):
    user = await create_test_user(permissions=[Permission.TEST_UPLOAD])
    db_session.expunge_all()

    found = await UserRepository(db_session).find_by_id(user.id)

    assert loaded(found)
    assert [grant.permission for grant in found.permissions] == [Permission.TEST_UPLOAD]


@pytest.mark.asyncio(loop_scope="session")
async def test_find_by_id_loads_permissions_for_an_identity_mapped_user(
    db_session, create_test_user
):
    user = await create_test_user(permissions=[Permission.TEST_UPLOAD])
    db_session.expunge_all()
    stale = await db_session.get(User, user.id)
    assert not loaded(stale)

    found = await UserRepository(db_session).find_by_id(user.id)

    assert found is stale
    assert loaded(found)


@pytest.mark.asyncio(loop_scope="session")
async def test_deleting_a_user_deletes_the_grants(db_session, create_test_user):
    user = await create_test_user(permissions=[Permission.TEST_UPLOAD, Permission.TAG_MANAGE])
    repository = UserRepository(db_session)

    await repository.delete(user)
    await db_session.commit()

    left = await db_session.execute(
        select(UserPermission).where(UserPermission.user_id == user.id)
    )
    assert left.scalars().all() == []


@pytest.mark.asyncio(loop_scope="session")
async def test_the_same_permission_may_be_granted_to_several_users(db_session, create_test_user):
    first = await create_test_user(email="first@ispras.ru", permissions=[Permission.TEST_UPLOAD])
    second = await create_test_user(email="second@ispras.ru", permissions=[Permission.TEST_UPLOAD])

    holders = await db_session.execute(
        select(UserPermission.user_id).where(
            UserPermission.permission == Permission.TEST_UPLOAD
        )
    )
    assert set(holders.scalars().all()) == {first.id, second.id}
