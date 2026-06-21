from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.memory_allocator.models import TestArtifact


class ArtifactRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def find_by_id(self, artifact_id: int) -> TestArtifact | None:
        artifact = await self.session.get(TestArtifact, artifact_id)
        return artifact

    def add(self, artifact: TestArtifact) -> None:
        self.session.add(artifact)

    async def delete(self, artifact: TestArtifact) -> None:
        await self.session.delete(artifact)

    async def list_all(self) -> Sequence[TestArtifact]:
        query = select(TestArtifact)
        result = await self.session.execute(query)
        return result.scalars().all()
