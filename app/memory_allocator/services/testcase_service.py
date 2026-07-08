from app.core.unit_of_work import UnitOfWork
from app.memory_allocator.exceptions import TagNotFoundError, TestNotFoundError
from app.memory_allocator.models import TestCase
from app.memory_allocator.schemas import TestDomain


class TestcaseService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def list_all(self) -> list[TestDomain]:
        tests = await self.uow.tests.list_all()
        return [TestDomain.model_validate(test) for test in tests]

    async def find_by_id(self, test_id: int) -> TestCase | None:
        return await self.uow.tests.find_by_id(test_id)

    async def get_by_id(self, test_id: int) -> TestDomain:
        test = await self.find_by_id(test_id)
        if not test:
            raise TestNotFoundError(test_id=test_id)
        return TestDomain.model_validate(test)

    async def attach_tag(self, test_id: int, tag_id: int) -> None:
        test = await self.uow.tests.find_with_tags(test_id)
        if test is None:
            raise TestNotFoundError(test_id)
        tag = await self.uow.tags.find_by_id(tag_id)
        if tag is None:
            raise TagNotFoundError(tag_id)
        if tag in test.tags:
            return
        test.tags.append(tag)
        await self.uow.commit()

    async def detach_tag(self, test_id: int, tag_id: int) -> None:
        test = await self.uow.tests.find_with_tags(test_id)
        if test is None:
            raise TestNotFoundError(test_id)
        tag = await self.uow.tags.find_by_id(tag_id)
        if tag is None:
            raise TagNotFoundError(tag_id)
        if tag not in test.tags:
            return
        test.tags.remove(tag)
        await self.uow.commit()
