import pytest

from app.memory_allocator.exceptions import PlatformNotFoundError
from app.memory_allocator.schemas import PlatformDetailDomain
from app.memory_allocator.services.platform_service import PlatformService
from tests.factories import make_platform


def _make_service(uow):
    return PlatformService(uow=uow)


@pytest.mark.asyncio
async def test_get_by_id_success(mock_uow):
    service = _make_service(mock_uow)
    platform = make_platform()
    mock_uow.platforms.find_by_id.return_value = platform

    result = await service.get_by_id(platform.id)

    assert isinstance(result, PlatformDetailDomain)
    assert result.id == platform.id
    assert result.config == {}
    assert result.created_at is not None
    assert result.mmu_family == "mips_r6000"
    assert result.page_size == 4096


@pytest.mark.asyncio
async def test_get_by_id_nonexisting_platform(mock_uow):
    service = _make_service(mock_uow)
    mock_uow.platforms.find_by_id.return_value = None

    with pytest.raises(PlatformNotFoundError):
        await service.get_by_id(1)


@pytest.mark.asyncio
async def test_list_all_success(mock_uow):
    service = _make_service(mock_uow)
    platform_1 = make_platform()
    platform_2 = make_platform(id=2, mmu_family="armv7a", page_size=9046)
    mock_uow.platforms.list_all.return_value = [platform_1, platform_2]

    result = await service.list_all()

    assert len(result) == 2
    assert isinstance(result[0], PlatformDetailDomain)
    assert isinstance(result[1], PlatformDetailDomain)
    assert result[0].created_at is not None
    assert result[1].created_at is not None
    assert [p.id for p in result] == [1, 2]
    assert [p.config for p in result] == [{}, {}]
    assert [p.mmu_family for p in result] == ["mips_r6000", "armv7a"]
    assert [p.page_size for p in result] == [4096, 9046]


@pytest.mark.asyncio
async def test_list_all_empty_success(mock_uow):
    service = _make_service(mock_uow)
    mock_uow.platforms.list_all.return_value = []

    result = await service.list_all()

    assert len(result) == 0
