from unittest.mock import AsyncMock, Mock

import pytest


@pytest.fixture
def mock_uow():
    uow = Mock()
    uow.users = Mock()
    uow.tests = Mock()
    uow.platforms = Mock()
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

    # platforms
    uow.platforms.find_by_mmu_family = AsyncMock()
    uow.platforms.add = Mock()
    uow.platforms.delete = AsyncMock()
    uow.platforms.get_or_create = AsyncMock()
    uow.platforms.list_all = AsyncMock()

    # tests
    uow.tests.find_by_id = AsyncMock()
    uow.tests.add = Mock()
    uow.tests.delete = AsyncMock()
    uow.tests.list_all = AsyncMock()

    return uow


@pytest.fixture
def mock_user_service():
    service = Mock()
    service.find_by_email = AsyncMock()
    return service
