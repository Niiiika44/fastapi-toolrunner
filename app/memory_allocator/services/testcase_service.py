from app.core.unit_of_work import UnitOfWork
from app.memory_allocator.schemas import TestDomain


class TestcaseService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def list_all(self) -> list[TestDomain]:
        tests = await self.uow.tests.list_all()
        return [TestDomain.model_validate(test) for test in tests]
