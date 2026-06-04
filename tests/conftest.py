import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from testcontainers.postgres import PostgresContainer

from app.core.config import settings
from app.db.database import Base


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
