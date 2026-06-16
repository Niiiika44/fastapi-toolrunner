import pytest

from app.memory_allocator.services import TestcaseService
from tests.factories import make_test


@pytest.mark.asyncio
async def test_list_all(mock_uow):
    expected = [make_test(), make_test(id=2)]
    mock_uow.tests.list_all.return_value = expected
    service = TestcaseService(mock_uow)
    tests = await service.list_all()
    assert tests == expected
    mock_uow.tests.list_all.assert_awaited_once() 
