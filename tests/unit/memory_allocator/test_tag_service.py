import pytest

from app.memory_allocator.exceptions import TagAlreadyExistsError, TagNotFoundError
from app.memory_allocator.schemas import TagDomain
from app.memory_allocator.services import TagService
from tests.factories import make_tag


def _make_service(uow):
    return TagService(uow=uow)


def _simulate_persist(tag):
    """Mimic DB-assigned fields on flush."""
    if tag.id is None:
        tag.id = 1


@pytest.mark.asyncio
async def test_create_success(mock_uow):
    service = _make_service(mock_uow)
    mock_uow.tags.find_by_name.return_value = None
    mock_uow.tags.add.side_effect = _simulate_persist
    tag_name = "low_ram"

    result = await service.create(tag_name)

    mock_uow.commit.assert_awaited_once()
    assert isinstance(result, TagDomain)
    assert result.id == 1
    assert result.name == tag_name


@pytest.mark.asyncio
async def test_create_existing_tag(mock_uow):
    service = _make_service(mock_uow)
    tag = make_tag()
    mock_uow.tags.find_by_name.return_value = tag

    with pytest.raises(TagAlreadyExistsError):
        await service.create(tag.name)

    mock_uow.tags.add.assert_not_called()
    mock_uow.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_by_id_success(mock_uow):
    service = _make_service(mock_uow)
    tag = make_tag()
    mock_uow.tags.find_by_id.return_value = tag

    result = await service.get_by_id(tag.id)

    assert isinstance(result, TagDomain)
    assert result.id == tag.id
    assert result.name == tag.name
    mock_uow.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_by_id_nonexisting_tag(mock_uow):
    service = _make_service(mock_uow)
    mock_uow.tags.find_by_id.return_value = None

    with pytest.raises(TagNotFoundError):
        await service.get_by_id(1)


@pytest.mark.asyncio
async def test_list_all_success(mock_uow):
    service = _make_service(mock_uow)
    tag_1 = make_tag()
    tag_2 = make_tag(id=2, name="another_tag")
    mock_uow.tags.list_all.return_value = [tag_1, tag_2]

    result = await service.list_all()

    assert len(result) == 2
    assert isinstance(result[0], TagDomain)
    assert isinstance(result[1], TagDomain)
    assert [tag.id for tag in result] == [1, 2]
    assert [tag.name for tag in result] == ["default_tag", "another_tag"]


@pytest.mark.asyncio
async def test_list_all_empty_success(mock_uow):
    service = _make_service(mock_uow)
    mock_uow.tags.list_all.return_value = []

    result = await service.list_all()

    assert len(result) == 0


@pytest.mark.asyncio
async def test_delete_success(mock_uow):
    service = _make_service(mock_uow)
    tag = make_tag()
    mock_uow.tags.find_by_id.return_value = tag

    await service.delete(tag.id)

    assert mock_uow.tags.delete.call_args.args[0] == tag
    mock_uow.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_delete_nonexisting(mock_uow):
    service = _make_service(mock_uow)
    mock_uow.tags.find_by_id.return_value = None

    with pytest.raises(TagNotFoundError):
        await service.delete(1)

    mock_uow.tags.delete.assert_not_awaited()
    mock_uow.commit.assert_not_awaited()
