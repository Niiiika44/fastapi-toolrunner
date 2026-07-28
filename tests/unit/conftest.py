from unittest.mock import AsyncMock, Mock

import pytest

from app.memory_allocator.checker import MockChecker


@pytest.fixture
def mock_uow():
    uow = Mock()
    uow.users = Mock()
    uow.tests = Mock()
    uow.platforms = Mock()
    uow.validations = Mock()
    uow.tags = Mock()
    uow.commit = AsyncMock()
    uow.rollback = AsyncMock()
    uow.refresh = AsyncMock()
    uow.flush = AsyncMock()

    # users
    uow.users.find_by_id = AsyncMock()
    uow.users.find_by_username = AsyncMock()
    uow.users.find_by_email = AsyncMock()
    uow.users.add = Mock()
    uow.users.delete = AsyncMock()
    uow.users.list_all = AsyncMock()

    # platforms
    uow.platforms.find_by_mmu_family = AsyncMock()
    uow.platforms.find_by_id = AsyncMock()
    uow.platforms.add = Mock()
    uow.platforms.delete = AsyncMock()
    uow.platforms.get_or_create = AsyncMock()
    uow.platforms.list_all = AsyncMock()

    # tests
    uow.tests.find_by_id = AsyncMock()
    uow.tests.find_for_processing = AsyncMock()
    uow.tests.find_with_tags = AsyncMock()
    uow.tests.add = Mock()
    uow.tests.delete = AsyncMock()
    uow.tests.list_filtered = AsyncMock()

    # validations
    uow.validations.add = Mock()
    uow.validations.find_by_id = AsyncMock()
    uow.validations.list_by_test = AsyncMock()

    # tags
    uow.tags.add = Mock()
    uow.tags.find_by_id = AsyncMock()
    uow.tags.find_by_name = AsyncMock()
    uow.tags.list_all = AsyncMock()
    uow.tags.delete = AsyncMock()

    return uow


@pytest.fixture
def mock_user_service():
    service = Mock()
    service.find_by_email = AsyncMock()
    return service


@pytest.fixture
def mock_storage():
    storage = Mock()
    storage.save = AsyncMock()
    storage.load = AsyncMock()
    storage.delete = AsyncMock()
    storage.exists = AsyncMock()
    return storage


@pytest.fixture
def mock_checker():
    checker = MockChecker(0)
    return checker
