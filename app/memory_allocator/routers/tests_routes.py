import io
from typing import Annotated

from fastapi import APIRouter, Depends, File, Query, Response, UploadFile, status
from fastapi.responses import RedirectResponse, StreamingResponse

from app.auth.dependencies import get_current_user
from app.core.openapi import error
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

router = APIRouter(
    prefix="/tests",
    tags=["tests"],
    responses={401: error("Missing, expired or invalid token")},
)


@router.get(
    "",
    response_model=PaginatedTestsResponse,
    summary="List test cases",
    description=(
        "All filters are optional and combine as AND. Within a single list filter the "
        "values combine as OR: `?statuses=PARSED&statuses=ERROR` returns test cases in "
        "either status. `name` matches a case-insensitive substring, `mine` limits the "
        "result to the test cases uploaded by the current user. "
        "`total` counts every match of the filters, ignoring `limit` and `offset`."
    ),
    responses={
        422: error("Request validation failed"),
    },
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
    response_model=TestResponse,
    summary="Upload a test case archive",
    description=(
        "Accepts a zip archive with a memory test case. Only `memin.yaml` is read "
        "synchronously, to resolve the platform; the archive itself is parsed in the "
        "background. The response is returned immediately with status `PENDING` and "
        "zeroed counters. Track the progress by polling `GET /tests/{test_id}` until the "
        "status becomes `PARSED` or `ERROR`, or subscribe to the status WebSocket "
        "(see README)."
    ),
    responses={
        400: error(
            "The file is not a zip archive, contains no memin.yaml, "
            "or the platform cannot be extracted from it"
        ),
        422: error("Request validation failed"),
    },
)
async def upload(
    file: UploadFile = File(..., description="Zip archive with the memory test case"),
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
    response_model=ValidationResponse,
    summary="Request a validation run",
    description=(
        "Queues a checker run and returns the validation result immediately, in status "
        "`PENDING`. Track the outcome by polling `GET /tests/{test_id}/validations`. "
        "Every run is appended to the history, so a test case may hold several results."
    ),
    responses={
        404: error("Test case not found"),
        409: error("Test case is not PARSED — there is nothing to validate"),
        422: error("Request validation failed"),
    },
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
    response_model=TestResponse,
    summary="Get a test case by id",
    description="Also used to poll the parsing status after an upload.",
    responses={
        404: error("Test case not found"),
        422: error("Request validation failed"),
    },
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
    summary="List validation results of a test case",
    description=(
        "Full validation history, newest runs included. `checker_version` tells which "
        "checker produced the result, which makes checker regressions comparable."
    ),
    responses={
        404: error("Test case not found"),
        422: error("Request validation failed"),
    },
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
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Attach a tag to a test case",
    description="Idempotent: attaching an already attached tag succeeds and changes nothing.",
    responses={
        404: error("Test case or tag not found"),
        422: error("Request validation failed"),
    },
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
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Detach a tag from a test case",
    description="Idempotent: detaching a tag that is not attached succeeds and changes nothing.",
    responses={
        404: error("Test case or tag not found"),
        422: error("Request validation failed"),
    },
)
async def detach_tag(
    test_id: int,
    tag_id: int,
    service: TestcaseService = Depends(get_test_service),
    _: User = Depends(get_current_user),
) -> None:
    await service.detach_tag(test_id, tag_id)


@router.get(
    "/{test_id}/export",
    response_class=StreamingResponse,
    summary="Download a test case as a zip archive",
    description=(
        "The archive is rebuilt from the stored artifacts — the originally uploaded zip "
        "is deleted once parsing succeeds. Artifacts missing from the storage are skipped."
    ),
    responses={
        200: {
            "description": "Zip archive rebuilt from the artifacts of the test case",
            "content": {"application/zip": {}},
            "headers": {
                "Content-Disposition": {
                    "description": 'attachment; filename="<test name>.zip"',
                    "schema": {"type": "string"},
                }
            },
        },
        404: error("Test case not found"),
        409: error("Test case is not PARSED — there is nothing to export"),
        422: error("Request validation failed"),
    },
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
    response_class=Response,
    summary="Download a single artifact",
    description=(
        "With an object storage backend the endpoint answers `302` with a presigned link; "
        "with the local backend it streams the bytes itself. Follow redirects (`curl -L`); "
        "the presigned link needs no application token and expires on its own."
    ),
    responses={
        200: {
            "description": "Artifact bytes (local storage backend)",
            "content": {"application/octet-stream": {}},
            "headers": {
                "Content-Disposition": {
                    "description": 'attachment; filename="<artifact name>"',
                    "schema": {"type": "string"},
                }
            },
        },
        302: {
            "description": "Redirect to a presigned storage link (object storage backend)",
            "headers": {
                "Location": {
                    "description": "Presigned URL, expires after a configured TTL",
                    "schema": {"type": "string"},
                }
            },
        },
        404: error(
            "Artifact not found, belongs to another test case, "
            "or is missing from the storage"
        ),
        422: error("Request validation failed"),
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
