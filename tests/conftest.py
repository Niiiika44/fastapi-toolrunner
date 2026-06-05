import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from testcontainers.postgres import PostgresContainer

from app.auth.access_token_encoder import create_access_token
from app.auth.hash_utils import get_password_hash
from app.core.config import settings
from app.db.database import Base, get_db
from app.main import app
from app.memory_allocator.models import Block, Module, Partition, Region, TestCase  # noqa: F401
from app.users.enums import UserJobTitle
from app.users.models import User


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def engine():
    container = PostgresContainer("postgres:15", driver="asyncpg")
    container.start()

    async_engine = create_async_engine(
        container.get_connection_url(), echo=settings.DEBUG, future=True
    )

    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield async_engine
    await async_engine.dispose()
    container.stop()


@pytest_asyncio.fixture(loop_scope="session")
async def db_session(engine):
    connection = await engine.connect()
    transaction = await connection.begin()
    session = AsyncSession(
        bind=connection,
        join_transaction_mode="create_savepoint",
        expire_on_commit=False,
    )
    yield session
    await session.close()
    await transaction.rollback()
    await connection.close()


@pytest_asyncio.fixture(loop_scope="session")
async def client(db_session):
    async def get_test_db():
        """Provides a test database session for dependency injection."""
        yield db_session

    app.dependency_overrides[get_db] = get_test_db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as async_client:
        yield async_client

    app.dependency_overrides.clear()


@pytest_asyncio.fixture(loop_scope="session")
async def create_test_user(db_session):
    async def _create(
        email="user@ispras.ru",
        password="password123",
        first_name="Nikita",
        last_name="Lebedev",
        job_title=UserJobTitle.DEVELOPER,
        is_superuser=False,
    ):
        username = email.rsplit("@")[0]
        hashed_passw = get_password_hash(password)
        user = User(
            username=username,
            email=email,
            password=hashed_passw,
            first_name=first_name,
            last_name=last_name,
            job_title=job_title,
            is_superuser=is_superuser,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        return user

    return _create


@pytest.fixture()
def auth_headers():
    def _headers(user):
        data_to_encode = {"sub": str(user.id)}
        access_token = create_access_token(
            data_to_encode,
            settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            settings.SECRET_KEY,
            settings.JWT_ALGORITHM,
        )
        return {"Authorization": f"Bearer {access_token}"}

    return _headers
