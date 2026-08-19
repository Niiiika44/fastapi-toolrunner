import pytest
from pydantic import ValidationError

from app.core.config import Settings

# Minimal valid field set
BASE = dict(
    APP_NAME="x",
    APP_PORT=8000,
    API_PREFIX="/api",
    DB_USER="u",
    DB_PASSWORD="p",
    DB_NAME="d",
    DB_HOST="postgres",
    DB_PORT=5432,
    JWT_ALGORITHM="HS256",
    ACCESS_TOKEN_EXPIRE_MINUTES=60,
    STORAGE_PATH="/data/storage",
    RABBITMQ_USER="u",
    RABBITMQ_PASSWORD="p",
    RABBITMQ_VHOST="/",
    RABBITMQ_HOST="rabbitmq",
    RABBITMQ_PORT=5672,
    FLOWER_USER="a",
    FLOWER_PASSWORD="p",
    FLOWER_PORT=5555,
    REDIS_HOST="redis",
    REDIS_PORT=6379,
    REDIS_PASSWORD="p",
    REDIS_CELERY_DB=0,
    REDIS_EVENTS_DB=1
)

REAL_KEY = "a" * 64


def _settings(**overrides):
    return Settings(_env_file=None, **{**BASE, **overrides})


def test_dev_config_allows_debug_and_weak_key():
    s = _settings(ENVIRONMENT="dev", DEBUG=True, SECRET_KEY="short")
    assert s.ENVIRONMENT == "dev"


def test_prod_with_safe_config_loads():
    s = _settings(ENVIRONMENT="prod", DEBUG=False, SECRET_KEY=REAL_KEY)
    assert s.ENVIRONMENT == "prod"


def test_prod_rejects_debug_true():
    with pytest.raises(ValidationError, match="DEBUG must be False"):
        _settings(ENVIRONMENT="prod", DEBUG=True, SECRET_KEY=REAL_KEY)


def test_prod_rejects_placeholder_secret():
    with pytest.raises(ValidationError, match="SECRET_KEY"):
        _settings(ENVIRONMENT="prod", DEBUG=False, SECRET_KEY="CHANGE-ME-run-openssl-rand-hex-32")


def test_prod_rejects_short_secret():
    with pytest.raises(ValidationError, match="SECRET_KEY"):
        _settings(ENVIRONMENT="prod", DEBUG=False, SECRET_KEY="tooshort")
