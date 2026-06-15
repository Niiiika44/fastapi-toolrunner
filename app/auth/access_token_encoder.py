import time

from jose import jwt


def create_access_token(
        data: dict,
        delta_expires: int,
        secret_key: str,
        jwt_algorithm: str
) -> str:
    data_to_encode = data.copy()
    expire = int(time.time()) + delta_expires
    data_to_encode.update({"exp": expire})
    jwt_encoded = jwt.encode(data_to_encode, secret_key, jwt_algorithm)
    return jwt_encoded


def decode_access_token(
        token: str,
        secret_key: str,
        jwt_algorithm: str
) -> dict:
    return jwt.decode(token, secret_key, algorithms=[jwt_algorithm])
