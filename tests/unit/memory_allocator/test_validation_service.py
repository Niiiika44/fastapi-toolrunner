from functools import partial
from unittest.mock import Mock

import pytest

from app.memory_allocator.enums import ValidationStatus
from app.memory_allocator.exceptions import TestNotFoundError, TestNotValidatableError
from app.memory_allocator.schemas import ValidationDomain
from app.memory_allocator.services import ValidationService
from tests.factories import make_test, make_validation_result


def _simulate_persist(vr, test):
    """Mimic DB-assigned fields on flush."""
    vr.id = 1
    vr.test_id = test.id


def _make_service(mock_uow, mock_checker, dispatch=None):
    return ValidationService(mock_uow, mock_checker, enqueue_validation=dispatch or Mock())


@pytest.mark.asyncio
async def test_request_validation_success(mock_uow, mock_checker):
    test = make_test(id=1, status="parsed")
    dispatch = Mock()
    service = _make_service(mock_uow, mock_checker, dispatch)
    mock_uow.validations.add.side_effect = partial(_simulate_persist, test=test)
    mock_uow.tests.find_by_id.return_value = test

    result = await service.request_validation(test.id)

    assert isinstance(result, ValidationDomain)
    assert result.status == "pending"
    assert result.valid is None
    assert result.schema_valid is None
    assert result.errors is None
    assert result.checker_version is None
    assert result.checked_at is None
    assert result.test_id == test.id
    orm_vr = mock_uow.validations.add.call_args.args[0]
    assert orm_vr.status == "pending"
    mock_uow.commit.assert_awaited_once()
    dispatch.assert_called_once_with(orm_vr.id)


@pytest.mark.asyncio
async def test_request_validation_nonexisting_test(mock_uow, mock_checker):
    test = make_test(id=1, status="parsed")
    dispatch = Mock()
    service = _make_service(mock_uow, mock_checker, dispatch)
    mock_uow.tests.find_by_id.return_value = None

    with pytest.raises(TestNotFoundError):
        await service.request_validation(test.id)

    mock_uow.validations.add.assert_not_called()
    mock_uow.commit.assert_not_awaited()
    dispatch.assert_not_called()


@pytest.mark.parametrize("status", ["pending", "processing", "error"])
@pytest.mark.asyncio
async def test_request_validation_rejects_non_parsed(mock_uow, mock_checker, status):
    test = make_test(id=1, status=status)
    dispatch = Mock()
    service = _make_service(mock_uow, mock_checker, dispatch)
    mock_uow.tests.find_by_id.return_value = test

    with pytest.raises(TestNotValidatableError):
        await service.request_validation(test.id)

    mock_uow.validations.add.assert_not_called()
    mock_uow.commit.assert_not_awaited()
    dispatch.assert_not_called()


@pytest.mark.asyncio
async def test_perform_validation_success(mock_uow, mock_checker):
    test = make_test(id=1, status="parsed")
    service = _make_service(mock_uow, mock_checker)
    vr = make_validation_result(
        test=test,
        status=ValidationStatus.PENDING,
        valid=None, schema_valid=None, errors=None,
        checker_version=None, checked_at=None,
    )
    mock_uow.validations.find_by_id.return_value = vr
    result = await service.perform_validation(vr.id)

    assert result is None
    assert vr.status == ValidationStatus.COMPLETED
    assert vr.valid is True
    assert vr.schema_valid is True
    assert vr.errors == []
    assert vr.checker_version == "mock-1.0"
    assert vr.checked_at is not None
    assert mock_uow.commit.await_count == 2


@pytest.mark.asyncio
async def test_perform_validation_completed(mock_uow, mock_checker):
    test = make_test(id=1, status="parsed")
    service = _make_service(mock_uow, mock_checker)
    vr = make_validation_result(
        test=test,
        status=ValidationStatus.COMPLETED,
        valid=False, schema_valid=True, errors=[],
        checker_version="mock-2.0", checked_at=None,
    )
    mock_uow.validations.find_by_id.return_value = vr
    result = await service.perform_validation(vr.id)

    assert result is None
    assert vr.status == ValidationStatus.COMPLETED
    assert vr.valid is False
    assert vr.schema_valid is True
    assert vr.errors == []
    assert vr.checker_version == "mock-2.0"
    assert vr.checked_at is None
    mock_uow.commit.assert_not_awaited()
    mock_uow.validations.add.assert_not_called()


@pytest.mark.asyncio
async def test_perform_validation_no_validation_result(mock_uow, mock_checker):
    service = _make_service(mock_uow, mock_checker)
    mock_uow.validations.find_by_id.return_value = None
    result = await service.perform_validation(1)

    assert result is None
    mock_uow.commit.assert_not_awaited()
    mock_uow.validations.add.assert_not_called()


@pytest.mark.asyncio
async def test_list_for_test_success(mock_uow, mock_checker):
    test = make_test()
    service = _make_service(mock_uow, mock_checker)
    vr_1 = make_validation_result(
        id=1,
        test=test,
        status=ValidationStatus.PENDING,
        valid=True, schema_valid=False, errors=[],
        checker_version="mock1"
    )
    vr_2 = make_validation_result(
        id=2,
        test=test,
        status=ValidationStatus.FAILED,
        valid=False, schema_valid=False, errors=["error"],
        checker_version="mock-2"
    )
    mock_uow.tests.find_by_id.return_value = test
    mock_uow.validations.list_by_test.return_value = [vr_1, vr_2]

    result = await service.list_for_test(test.id)

    assert len(result) == 2
    assert isinstance(result[0], ValidationDomain) and isinstance(result[1], ValidationDomain)
    assert {vr_1.status, vr_2.status} == {result[0].status, result[1].status}
    assert result[1].checker_version == vr_2.checker_version
    assert result[0].checker_version == vr_1.checker_version
    assert test.id == result[0].test_id == result[1].test_id
    mock_uow.commit.assert_not_awaited()
    mock_uow.validations.add.assert_not_called()


@pytest.mark.asyncio
async def test_list_for_test_nonexisting_test_id(mock_uow, mock_checker):
    service = _make_service(mock_uow, mock_checker)
    mock_uow.tests.find_by_id.return_value = None
    with pytest.raises(TestNotFoundError):
        await service.list_for_test(1)
