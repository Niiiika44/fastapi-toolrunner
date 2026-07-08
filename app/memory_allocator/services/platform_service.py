from app.core.unit_of_work import UnitOfWork
from app.memory_allocator.exceptions import PlatformNotFoundError
from app.memory_allocator.schemas import PlatformDetailDomain


class PlatformService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def get_by_id(self, platform_id: int) -> PlatformDetailDomain:
        platform = await self.uow.platforms.find_by_id(platform_id)
        if not platform:
            raise PlatformNotFoundError(platform_id)
        return PlatformDetailDomain.model_validate(platform)

    async def list_all(self) -> list[PlatformDetailDomain]:
        platforms = await self.uow.platforms.list_all()
        return [PlatformDetailDomain.model_validate(platform) for platform in platforms]
