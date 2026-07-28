import pytest

from app.memory_allocator.exceptions import TagNotFoundError, TestNotFoundError
from app.memory_allocator.schemas import TestDomain, TestFilter, TestPagination
from app.memory_allocator.services import TestcaseService
from tests.factories import make_tag, make_test, make_user


@pytest.mark.asyncio
async def test_list_tests(mock_uow, ):
    expected = [make_test(), make_test(id=2)]
    mock_uow.tests.list_filtered.return_value = (expected, 2)
    service = TestcaseService(mock_uow)
    pagination = TestPagination()
    filters = TestFilter()
    user = make_user()
    tests, total = await service.list_tests(
        filters=filters, pagination=pagination, current_user=user
    )
    assert all(isinstance(test, TestDomain) for test in tests)
    assert [test.id for test in tests] == [1, 2]
    assert total == len(expected) == 2
    mock_uow.tests.list_filtered.assert_awaited_once()
    assert mock_uow.tests.list_filtered.await_args.kwargs["user_id"] == user.id


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


@pytest.mark.asyncio
async def test_attach_tag_success(mock_uow):
    service = TestcaseService(mock_uow)
    test = make_test()
    tag = make_tag()
    mock_uow.tests.find_with_tags.return_value = test
    mock_uow.tags.find_by_id.return_value = tag

    await service.attach_tag(test.id, tag.id)

    assert tag in test.tags
    mock_uow.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_attach_tag_success_idempotency(mock_uow):
    service = TestcaseService(mock_uow)
    test = make_test()
    tag = make_tag()
    mock_uow.tests.find_with_tags.return_value = test
    mock_uow.tags.find_by_id.return_value = tag

    await service.attach_tag(test.id, tag.id)
    await service.attach_tag(test.id, tag.id)

    assert test.tags == [tag]
    mock_uow.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_attach_tag_nonexisting_test(mock_uow):
    service = TestcaseService(mock_uow)
    mock_uow.tests.find_with_tags.return_value = None

    with pytest.raises(TestNotFoundError):
        await service.attach_tag(1, 1)

    mock_uow.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_attach_tag_nonexisting_tag(mock_uow):
    service = TestcaseService(mock_uow)
    test = make_test()
    mock_uow.tests.find_with_tags.return_value = test
    mock_uow.tags.find_by_id.return_value = None

    with pytest.raises(TagNotFoundError):
        await service.attach_tag(test.id, 1)

    mock_uow.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_detach_tag_success(mock_uow):
    service = TestcaseService(mock_uow)
    tag = make_tag()
    test = make_test(tags=[tag])
    mock_uow.tests.find_with_tags.return_value = test
    mock_uow.tags.find_by_id.return_value = tag

    await service.detach_tag(test.id, tag.id)

    assert tag not in test.tags
    mock_uow.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_detach_tag_success_idempotency(mock_uow):
    service = TestcaseService(mock_uow)
    tag = make_tag()
    test = make_test(tags=[tag])
    mock_uow.tests.find_with_tags.return_value = test
    mock_uow.tags.find_by_id.return_value = tag

    await service.detach_tag(test.id, tag.id)
    await service.detach_tag(test.id, tag.id)

    assert tag not in test.tags
    mock_uow.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_detach_tag_nonexisting_test(mock_uow):
    service = TestcaseService(mock_uow)
    mock_uow.tests.find_with_tags.return_value = None

    with pytest.raises(TestNotFoundError):
        await service.detach_tag(1, 1)

    mock_uow.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_detach_tag_nonexisting_tag(mock_uow):
    service = TestcaseService(mock_uow)
    test = make_test()
    mock_uow.tests.find_with_tags.return_value = test
    mock_uow.tags.find_by_id.return_value = None

    with pytest.raises(TagNotFoundError):
        await service.detach_tag(test.id, 1)

    mock_uow.commit.assert_not_awaited()
