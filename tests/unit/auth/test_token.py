import pytest
from jose import JWTError

from app.auth.access_token_encoder import create_access_token, decode_access_token
from app.core.config import settings


def test_sub_token_content():
    data_to_encode = {"sub": "test_data"}
    access_token = create_access_token(
        data_to_encode,
        settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        settings.SECRET_KEY,
        settings.JWT_ALGORITHM
    )
    assert isinstance(access_token, str)

    decoded_data = decode_access_token(
        access_token, settings.SECRET_KEY, settings.JWT_ALGORITHM
    )
    assert data_to_encode["sub"] == decoded_data["sub"]


def test_expired_token():
    data_to_encode = {"sub": "test_data"}
    expired_time = -1
    access_token = create_access_token(
        data_to_encode,
        expired_time,
        settings.SECRET_KEY,
        settings.JWT_ALGORITHM
    )
    assert isinstance(access_token, str)

    with pytest.raises(JWTError):
        decode_access_token(
            access_token, settings.SECRET_KEY, settings.JWT_ALGORITHM
        )


@pytest.mark.parametrize("invalid_token", [
    "garbage", "not.a.jwt", "",
])
def test_invalid_token_raises(invalid_token):
    with pytest.raises(JWTError):
        decode_access_token(
            invalid_token, settings.SECRET_KEY, settings.JWT_ALGORITHM
        )
