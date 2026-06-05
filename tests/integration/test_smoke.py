import pytest
from sqlalchemy import select
from app.users.models import User


@pytest.mark.asyncio(loop_scope="session")
async def test_health(client):
    health_info = await client.get("/health")
    assert health_info.status_code == 200


@pytest.mark.asyncio(loop_scope="session")
async def test_create_user_fixture(create_test_user, db_session):
    created_user = await create_test_user(email="test@ispras.ru")
    db_session.expunge_all()
    assert created_user.id is not None

    result = await db_session.execute(
        select(User).where(User.email == created_user.email)
    )
    db_user = result.scalar_one_or_none()
    assert db_user is not None
    assert db_user.id == created_user.id


@pytest.mark.asyncio(loop_scope="session")
async def test_isolation(db_session):
    result = await db_session.execute(select(User))
    existed_user = result.scalar_one_or_none()
    assert existed_user is None
