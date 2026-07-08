import pytest
from fastapi import status

from app.memory_allocator.enums import TestStatus, ValidationStatus
from tests.conftest import assert_error_response
from tests.factories import make_test, make_validation_result


@pytest.mark.asyncio(loop_scope="session")
async def test_validate_success(
    client,
    db_session,
    create_test_user,
    auth_headers,
    override_validation_dispatch,
):
    user = await create_test_user()
    test = make_test(status=TestStatus.PARSED, uploaded_by=user)
    db_session.add(test)
    await db_session.commit()

    response = await client.post(
        f"/tests/{test.id}/validate",
        headers=auth_headers(user),
    )
    assert response.status_code == status.HTTP_202_ACCEPTED
    body = response.json()
    assert body["status"] == ValidationStatus.PENDING
    assert body["valid"] is None
    assert body["schema_valid"] is None
    assert body["errors"] is None
    assert body["checker_version"] is None
    assert body["checked_at"] is None
    assert body["test_id"] == test.id
    override_validation_dispatch.assert_called_once()


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.usefixtures("override_validation_dispatch")
async def test_validate_nonexisting_test(
    client,
    create_test_user,
    auth_headers,
):
    user = await create_test_user()

    response = await client.post(
        "/tests/1/validate",
        headers=auth_headers(user),
    )
    assert_error_response(response, status.HTTP_404_NOT_FOUND)


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.parametrize("test_status", [
    TestStatus.PENDING,
    TestStatus.ERROR,
    TestStatus.PROCESSING,
])
@pytest.mark.usefixtures("override_validation_dispatch")
async def test_validate_test_status_not_parsed(
    test_status,
    client,
    db_session,
    create_test_user,
    auth_headers,
):
    user = await create_test_user()
    test = make_test(status=test_status, uploaded_by=user)
    db_session.add(test)
    await db_session.commit()

    response = await client.post(
        f"/tests/{test.id}/validate",
        headers=auth_headers(user),
    )
    assert_error_response(response, status.HTTP_409_CONFLICT)


@pytest.mark.asyncio(loop_scope="session")
async def test_validate_no_user(
    client,
):
    response = await client.post("/tests/1/validate")
    assert_error_response(response, status.HTTP_401_UNAUTHORIZED)


@pytest.mark.asyncio(loop_scope="session")
async def test_list_validations_success(
    client,
    db_session,
    create_test_user,
    auth_headers,
):
    user = await create_test_user()
    test = make_test(status=TestStatus.PARSED, uploaded_by=user)
    vr_1 = make_validation_result(test=test, status=ValidationStatus.COMPLETED)
    vr_2 = make_validation_result(test=test, id=2, status=ValidationStatus.FAILED)
    db_session.add_all([test, vr_1, vr_2])
    await db_session.commit()

    response = await client.get(
        f"/tests/{test.id}/validations",
        headers=auth_headers(user),
    )
    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert len(body) == 2
    assert {el["status"] for el in body} == {"failed", "completed"}
    assert [el["id"] for el in body] == [2, 1]


@pytest.mark.asyncio(loop_scope="session")
async def test_list_validations_success_empty(
    client,
    db_session,
    create_test_user,
    auth_headers,
):
    user = await create_test_user()
    test = make_test(status=TestStatus.PARSED, uploaded_by=user)
    db_session.add(test)
    await db_session.commit()

    response = await client.get(
        f"/tests/{test.id}/validations",
        headers=auth_headers(user),
    )
    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert len(body) == 0


@pytest.mark.asyncio(loop_scope="session")
async def test_list_validations_no_user(
    client,
):
    response = await client.get("/tests/1/validations")
    assert_error_response(response, status.HTTP_401_UNAUTHORIZED)
