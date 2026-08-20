import io
from typing import Annotated

from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from fastapi.responses import RedirectResponse, StreamingResponse

from app.auth.dependencies import get_current_user
from app.memory_allocator.dependencies import (
    get_export_service,
    get_ingestion_service,
    get_test_service,
    get_validation_service,
)
from app.memory_allocator.schemas import (
    ArtifactLinkDomain,
    PaginatedTestsResponse,
    TestListQuery,
    TestPagination,
    TestResponse,
    ValidationResponse,
)
from app.memory_allocator.services import IngestionService, TestcaseService, ValidationService
from app.memory_allocator.services.export_service import ExportService
from app.users.models import User

router = APIRouter(prefix="/tests", tags=["tests"])


@router.get(
    "",
    response_model=PaginatedTestsResponse
)
async def list_all(
    query: Annotated[TestListQuery, Query()],
    service: TestcaseService = Depends(get_test_service),
    current_user: User = Depends(get_current_user),
) -> PaginatedTestsResponse:
    pagination = TestPagination(limit=query.limit, offset=query.offset)
    tests, total = await service.list_tests(query, pagination, current_user)
    return PaginatedTestsResponse(
        tests=[TestResponse.model_validate(t) for t in tests],
        total=total,
        limit=pagination.limit,
        offset=pagination.offset
    )


@router.post(
    "/upload",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=TestResponse
)
async def upload(
    file: UploadFile = File(...),
    service: IngestionService = Depends(get_ingestion_service),
    current_user: User = Depends(get_current_user)
) -> TestResponse:
    test = await service.accept_upload(
        file=file,
        uploaded_by=current_user
    )
    return TestResponse.model_validate(test)


@router.post(
    "/{test_id}/validate",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=ValidationResponse
)
async def validate(
    test_id: int,
    service: ValidationService = Depends(get_validation_service),
    _: User = Depends(get_current_user)
) -> ValidationResponse:
    validation = await service.request_validation(test_id)
    return ValidationResponse.model_validate(validation)


@router.get(
    "/{test_id}",
    response_model=TestResponse
)
async def get_test_by_id(
    test_id: int,
    service: TestcaseService = Depends(get_test_service),
    _: User = Depends(get_current_user)
) -> TestResponse:
    test = await service.get_by_id(test_id=test_id)
    return TestResponse.model_validate(test)


@router.get(
    "/{test_id}/validations",
    response_model=list[ValidationResponse],
)
async def list_validations(
    test_id: int,
    service: ValidationService = Depends(get_validation_service),
    _: User = Depends(get_current_user),
) -> list[ValidationResponse]:
    validations = await service.list_for_test(test_id)
    return [ValidationResponse.model_validate(vr) for vr in validations]


@router.post(
    "/{test_id}/tags/{tag_id}",
    status_code=status.HTTP_204_NO_CONTENT
)
async def attach_tag(
    test_id: int,
    tag_id: int,
    service: TestcaseService = Depends(get_test_service),
    _: User = Depends(get_current_user),
) -> None:
    await service.attach_tag(test_id, tag_id)


@router.delete(
    "/{test_id}/tags/{tag_id}",
    status_code=status.HTTP_204_NO_CONTENT
)
async def detach_tag(
    test_id: int,
    tag_id: int,
    service: TestcaseService = Depends(get_test_service),
    _: User = Depends(get_current_user),
) -> None:
    await service.detach_tag(test_id, tag_id)


@router.get(
    "/{test_id}/export"
)
async def export_testcase(
    test_id: int,
    service: ExportService = Depends(get_export_service),
    _: User = Depends(get_current_user),
) -> StreamingResponse:
    buffer, filename = await service.export_test(test_id)
    return StreamingResponse(
        buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get(
    "/{test_id}/artifacts/{artifact_id}/download",
    response_model=None,
    responses={
        200: {"description": "Файл потоком (локальное хранилище)"},
        302: {"description": "Редирект на presigned-ссылку хранилища (S3)"},
        404: {"description": "Артефакт не найден или принадлежит другому тесту"},
    },
)
async def download_artifact(
    test_id: int,
    artifact_id: int,
    service: ExportService = Depends(get_export_service),
    _: User = Depends(get_current_user),
) -> RedirectResponse | StreamingResponse:
    artifact = await service.artifact_download(test_id, artifact_id)
    if isinstance(artifact, ArtifactLinkDomain):
        return RedirectResponse(artifact.url, status_code=status.HTTP_302_FOUND)
    return StreamingResponse(
        io.BytesIO(artifact.content),
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{artifact.filename}"'},
    )
