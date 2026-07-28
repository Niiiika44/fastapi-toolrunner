import io
import logging
import zipfile

from app.core.storage import StorageBackend
from app.core.unit_of_work import UnitOfWork
from app.memory_allocator.enums import TestStatus
from app.memory_allocator.exceptions import ExportNotAvailableError, TestNotFoundError

logger = logging.getLogger(__name__)


class ExportService:
    def __init__(self, uow: UnitOfWork, storage: StorageBackend):
        self.uow = uow
        self.storage = storage

    async def export_test(self, test_id: int) -> tuple[io.BytesIO, str]:
        test = await self.uow.tests.find_by_id(test_id)
        if test is None:
            raise TestNotFoundError(test_id)
        if test.status != TestStatus.PARSED:
            raise ExportNotAvailableError(test_id)

        artifacts = await self.uow.artifacts.list_by_test(test_id)

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for a in artifacts:
                try:
                    content = await self.storage.load(a.storage_key)
                    zf.writestr(a.filename, content)
                except KeyError:
                    logger.error("No test %s artifact: %s", test_id, a)
        buf.seek(0)
        return buf, f"{test.name}.zip"
