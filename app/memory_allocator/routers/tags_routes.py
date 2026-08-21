from fastapi import APIRouter, Depends, status

from app.auth.dependencies import get_current_user
from app.core.openapi import error
from app.memory_allocator.dependencies import get_tag_service
from app.memory_allocator.schemas import TagCreate, TagResponse
from app.memory_allocator.services import TagService
from app.users.models import User

router = APIRouter(
    prefix="/tags",
    tags=["tags"],
    responses={401: error("Missing, expired or invalid token")},
)


@router.post(
    "",
    response_model=TagResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a tag",
    description="Tag names are unique across the whole service.",
    responses={
        409: error("Tag with this name already exists"),
        422: error("Request validation failed"),
    },
)
async def create_tag(
    tag_data: TagCreate,
    service: TagService = Depends(get_tag_service),
    _: User = Depends(get_current_user),
) -> TagResponse:
    tag = await service.create(tag_data.name)
    return TagResponse.model_validate(tag)


@router.get(
    "",
    response_model=list[TagResponse],
    summary="List tags",
)
async def list_all(
    service: TagService = Depends(get_tag_service),
    _: User = Depends(get_current_user),
) -> list[TagResponse]:
    tags = await service.list_all()
    return [TagResponse.model_validate(tag) for tag in tags]


@router.get(
    "/{tag_id}",
    response_model=TagResponse,
    summary="Get a tag by id",
    responses={
        404: error("Tag not found"),
        422: error("Request validation failed"),
    },
)
async def get_tag_by_id(
    tag_id: int,
    service: TagService = Depends(get_tag_service),
    _: User = Depends(get_current_user),
) -> TagResponse:
    tag = await service.get_by_id(tag_id)
    return TagResponse.model_validate(tag)


@router.delete(
    "/{tag_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a tag",
    responses={
        404: error("Tag not found"),
        422: error("Request validation failed"),
    },
)
async def delete_tag_by_id(
    tag_id: int,
    service: TagService = Depends(get_tag_service),
    _: User = Depends(get_current_user),
) -> None:
    await service.delete(tag_id)
