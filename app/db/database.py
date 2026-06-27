from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool

from app.core.config import get_settings

settings = get_settings()


engine = create_async_engine(
    settings.DB_URL,
    echo=settings.DEBUG,
    future=True
)
worker_engine = create_async_engine(
    settings.DB_URL,
    poolclass=NullPool
)


AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)
WorkerSessionLocal = async_sessionmaker(
    bind=worker_engine,
    class_=AsyncSession,
    expire_on_commit=False
)


Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Provides a database session for dependency injection."""
    async with AsyncSessionLocal() as session:
        yield session
