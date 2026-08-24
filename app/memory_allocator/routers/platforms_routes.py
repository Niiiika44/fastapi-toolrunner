from fastapi import APIRouter, Depends

from app.auth.dependencies import require
from app.auth.enums import Permission
from app.core.openapi import error
from app.memory_allocator.dependencies import get_platform_service
from app.memory_allocator.schemas import PlatformDetailResponse
from app.memory_allocator.services import PlatformService
from app.users.models import User

router = APIRouter(
    prefix="/platforms",
    tags=["platforms"],
    responses={401: error("Missing, expired or invalid token")},
)


@router.get(
    "",
    response_model=list[PlatformDetailResponse],
    summary="List platforms",
    description=(
        "Platforms are read-only: a row is created automatically on upload, "
        "deduplicated by `mmu_family`. Requires the `platform:read` permission."
    ),
    responses={
        403: error("Requires the platform:read permission"),
    },
)
async def list_all(
    service: PlatformService = Depends(get_platform_service),
    _: User = Depends(require(Permission.PLATFORM_READ)),
) -> list[PlatformDetailResponse]:
    platforms = await service.list_all()
    return [PlatformDetailResponse.model_validate(platform) for platform in platforms]


@router.get(
    "/{platform_id}",
    response_model=PlatformDetailResponse,
    summary="Get a platform by id",
    responses={
        403: error("Requires the platform:read permission"),
        404: error("Platform not found"),
        422: error("Request validation failed"),
    },
)
async def get_platform_by_id(
    platform_id: int,
    service: PlatformService = Depends(get_platform_service),
    _: User = Depends(require(Permission.PLATFORM_READ)),
) -> PlatformDetailResponse:
    platform = await service.get_by_id(platform_id)
    return PlatformDetailResponse.model_validate(platform)
