from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.orm import declarative_base

from app.core.config import settings


engine = create_async_engine(
    settings.DB_URL,
    echo=settings.DEBUG,
    future=True
)


AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)


Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Provides a database session for dependency injection."""
    async with AsyncSessionLocal() as session:
        yield session
