import io
import logging
import time
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
        started_at = time.monotonic()
        test = await self.uow.tests.find_by_id(test_id)
        if test is None:
            raise TestNotFoundError(test_id)
        if test.status != TestStatus.PARSED:
            logger.warning("export.rejected", extra={"test_id": test.id, "status": test.status})
            raise ExportNotAvailableError(test_id)

        artifacts = await self.uow.artifacts.list_by_test(test_id)

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for a in artifacts:
                try:
                    content = await self.storage.load(a.storage_key)
                    zf.writestr(a.filename, content)
                except KeyError:
                    logger.warning("export.artifact_missing", extra={
                        "test_id": test.id,
                        "storage_key": str(a.storage_key)
                    })
        buf.seek(0)
        logger.info("test.exported", extra={
            "test_id": test.id,
            "artifact_count": len(artifacts),
            "size_bytes": buf.getbuffer().nbytes,
            "duration_ms": round((time.monotonic() - started_at) * 1000)
        })
        return buf, f"{test.name}.zip"
