import tempfile
import zipfile
from pathlib import Path

import aiofiles
from fastapi import APIRouter, Depends, File, UploadFile

from app.auth.dependencies import get_current_user
from app.memory_allocator.dependencies import get_ingestion_service, get_test_service
from app.memory_allocator.exceptions import InvalidUploadError
from app.memory_allocator.schemas import TestResponse
from app.memory_allocator.services import IngestionService, TestcaseService
from app.users.models import User

router = APIRouter(prefix="/tests", tags=["tests"])


@router.get("",
            response_model=list[TestResponse])
async def list_all(
    service: TestcaseService = Depends(get_test_service),
    _: User = Depends(get_current_user),
) -> list[TestResponse]:
    tests = await service.list_all()
    return list(tests)


@router.post("/upload",
             response_model=TestResponse)
async def upload(
    file: UploadFile = File(...),
    service: IngestionService = Depends(get_ingestion_service),
    current_user: User = Depends(get_current_user)
) -> TestResponse:
    if not (file.filename and file.filename.endswith(".zip")):
        raise InvalidUploadError(str(file.filename), "only zip files could be attached")

    with tempfile.TemporaryDirectory() as tmpdir:
        zip_path = Path(tmpdir, file.filename)
        async with aiofiles.open(zip_path, "wb") as f:
            await f.write(await file.read())

        extract_dir = Path(tmpdir, "extracted")
        extract_dir.mkdir()

        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(extract_dir)

        test = await service.ingest(
            folder_path=extract_dir,
            test_name=Path(file.filename).stem,
            uploaded_by=current_user
        )
        return test
