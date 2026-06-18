import pytest

from app.auth.access_token_encoder import decode_access_token
from app.auth.exceptions import InvalidCredentialsError
from app.auth.schemas import TokenResponse
from app.auth.services import AuthService
from app.core.config import get_settings
from tests.factories import DEFAULT_PASSWORD, make_user

settings = get_settings()


@pytest.mark.asyncio
async def test_authenticate_user_success(mock_user_service):
    user = make_user()
    mock_user_service.find_by_email.return_value = user
    service = AuthService(mock_user_service)
    token = await service.authenticate_user(user.email, DEFAULT_PASSWORD)
    mock_user_service.find_by_email.assert_awaited_once_with(user.email)
    assert isinstance(token, TokenResponse)
    assert isinstance(token.access_token, str)
    assert len(token.access_token) > 0
    assert token.token_type == "bearer"


@pytest.mark.asyncio
async def test_authenticate_nonexistent_user(mock_user_service):
    mock_user_service.find_by_email.return_value = None
    service = AuthService(mock_user_service)
    with pytest.raises(InvalidCredentialsError):
        await service.authenticate_user("not_existent_email@ispras.ru", DEFAULT_PASSWORD)


@pytest.mark.asyncio
async def test_authenticate_user_wrong_password(mock_user_service):
    user = make_user()
    mock_user_service.find_by_email.return_value = user
    service = AuthService(mock_user_service)
    with pytest.raises(InvalidCredentialsError):
        await service.authenticate_user(user.email, "not a user password")
    mock_user_service.find_by_email.assert_awaited_once_with(user.email)


@pytest.mark.asyncio
async def test_authenticate_user_correct_payload(mock_user_service):
    user = make_user()
    mock_user_service.find_by_email.return_value = user
    service = AuthService(mock_user_service)
    token = await service.authenticate_user(user.email, DEFAULT_PASSWORD)
    decoded_data = decode_access_token(
        token.access_token, settings.SECRET_KEY, settings.JWT_ALGORITHM
    )
    assert isinstance(decoded_data, dict)
    assert "exp" in decoded_data and "sub" in decoded_data
    assert decoded_data["sub"] == str(user.id)
