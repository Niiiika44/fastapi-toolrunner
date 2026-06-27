import io
import shutil
import zipfile
from pathlib import Path
from unittest.mock import Mock

import pytest
import pytest_asyncio
from fastapi import Depends
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from testcontainers.postgres import PostgresContainer

from app.auth.access_token_encoder import create_access_token
from app.auth.hash_utils import get_password_hash
from app.core.config import get_settings
from app.core.dependencies import get_storage, get_uow
from app.core.storage import LocalStorage, StorageBackend
from app.core.unit_of_work import UnitOfWork
from app.db.database import Base, get_db
from app.main import app
from app.memory_allocator.dependencies import get_ingestion_service
from app.memory_allocator.models import Block, Module, Partition, Region, TestCase  # noqa: F401
from app.memory_allocator.services import IngestionService
from app.users.enums import UserJobTitle
from app.users.models import User
from tests.factories import DEFAULT_PASSWORD

DATA_DIR = Path(__file__).parent / "data"

settings = get_settings()


@pytest.fixture
def data_dir() -> Path:
    return DATA_DIR


@pytest.fixture
def example_correct_folder(tmp_path):
    correct_folder = DATA_DIR / "mips_valid_example"
    shutil.copytree(
        correct_folder,
        tmp_path,
        copy_function=shutil.copy2,
        dirs_exist_ok=True
    )
    return tmp_path


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
        email="test@ispras.ru",
        password=DEFAULT_PASSWORD,
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


@pytest.fixture
def override_storage(tmp_path):
    app.dependency_overrides[get_storage] = lambda: LocalStorage(tmp_path)
    yield
    app.dependency_overrides.pop(get_storage, None)


@pytest.fixture
def override_dispatch():
    dispatch = Mock()

    def _factory(
        uow: UnitOfWork = Depends(get_uow),
        storage: StorageBackend = Depends(get_storage),
    ) -> IngestionService:
        return IngestionService(uow, storage, enqueue_processing=dispatch)

    app.dependency_overrides[get_ingestion_service] = _factory
    yield dispatch
    app.dependency_overrides.pop(get_ingestion_service, None)


def assert_error_response(response, status_code):
    assert response.status_code == status_code
    assert "message" in response.json()["error"]


def make_zip(folder: Path) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for f in folder.iterdir():
            zf.write(f, arcname=f.name)
    return buf.getvalue()
