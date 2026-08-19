import logging

from app.core.unit_of_work import UnitOfWork
from app.memory_allocator.exceptions import TagAlreadyExistsError, TagNotFoundError
from app.memory_allocator.models import Tag
from app.memory_allocator.schemas import TagDomain

logger = logging.getLogger(__name__)


class TagService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def create(self, tag_name: str) -> TagDomain:
        existing_tag = await self.uow.tags.find_by_name(tag_name)
        if existing_tag is not None:
            logger.warning("tag.create_rejected", extra={
                "tag_id": existing_tag.id, "tag_name": existing_tag.name
            })
            raise TagAlreadyExistsError(tag_name)
        tag = Tag(name=tag_name)
        self.uow.tags.add(tag)
        await self.uow.commit()
        await self.uow.refresh(tag)
        logger.info("tag.created", extra={"tag_id": tag.id, "tag_name": tag.name})
        return TagDomain.model_validate(tag)

    async def get_by_id(self, tag_id: int) -> TagDomain:
        tag = await self.uow.tags.find_by_id(tag_id)
        if tag is None:
            raise TagNotFoundError(tag_id)
        return TagDomain.model_validate(tag)

    async def list_all(self) -> list[TagDomain]:
        tags = await self.uow.tags.list_all()
        return [TagDomain.model_validate(tag) for tag in tags]

    async def delete(self, tag_id: int) -> None:
        tag = await self.uow.tags.find_by_id(tag_id)
        if tag is None:
            raise TagNotFoundError(tag_id)
        await self.uow.tags.delete(tag)
        await self.uow.commit()
        logger.info("tag.deleted", extra={"tag_id": tag.id, "tag_name": tag.name})
