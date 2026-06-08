import pytest
from unittest.mock import Mock, AsyncMock


@pytest.fixture
def mock_uow():
    uow = Mock()
    uow.users = Mock()
    uow.commit = AsyncMock()
    uow.rollback = AsyncMock()
    uow.refresh = AsyncMock()

    # users
    uow.users.find_by_id = AsyncMock()
    uow.users.find_by_username = AsyncMock()
    uow.users.find_by_email = AsyncMock()
    uow.users.add = Mock()
    uow.users.delete = AsyncMock()
    uow.users.list_all = AsyncMock()

    return uow


@pytest.fixture
def mock_user_service():
    service = Mock()
    service.find_by_email = AsyncMock()
    return service
