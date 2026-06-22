from fastapi import APIRouter, Depends, File, UploadFile

from app.auth.dependencies import get_current_user
from app.memory_allocator.dependencies import get_ingestion_service, get_test_service
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
    return [TestResponse.model_validate(test) for test in tests]


@router.post("/upload",
             response_model=TestResponse)
async def upload(
    file: UploadFile = File(...),
    service: IngestionService = Depends(get_ingestion_service),
    current_user: User = Depends(get_current_user)
) -> TestResponse:
    test = await service.ingest(
        file=file,
        uploaded_by=current_user
    )
    return TestResponse.model_validate(test)
