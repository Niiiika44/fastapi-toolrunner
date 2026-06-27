import pytest

from app.memory_allocator.exceptions import TestNotFoundError
from app.memory_allocator.schemas import TestDomain
from app.memory_allocator.services import TestcaseService
from tests.factories import make_test


@pytest.mark.asyncio
async def test_list_all(mock_uow):
    expected = [make_test(), make_test(id=2)]
    mock_uow.tests.list_all.return_value = expected
    service = TestcaseService(mock_uow)
    result = await service.list_all()
    assert all(isinstance(test, TestDomain) for test in result)
    assert [test.id for test in result] == [1, 2]
    mock_uow.tests.list_all.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_by_id_found(mock_uow):
    test = make_test(id=1)
    mock_uow.tests.find_by_id.return_value = test
    service = TestcaseService(mock_uow)
    result = await service.get_by_id(test.id)
    assert isinstance(result, TestDomain)
    assert result.id == 1


@pytest.mark.asyncio
async def test_get_by_id_not_found(mock_uow):
    mock_uow.tests.find_by_id.return_value = None
    service = TestcaseService(mock_uow)
    with pytest.raises(TestNotFoundError):
        await service.get_by_id(1)
