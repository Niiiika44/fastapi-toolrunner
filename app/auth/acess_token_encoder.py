import time
from jose import jwt


def create_acess_token(data: dict, delta_expires: int, secret_key: str, jwt_algorithm: str) -> str:
    data_to_encode = data.copy()
    expire = int(time.time()) + delta_expires
    data_to_encode.update({"exp": expire})
    jwt_encoded = jwt.encode(data_to_encode, secret_key, jwt_algorithm)
    return jwt_encoded

