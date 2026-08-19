from functools import lru_cache
from typing import Literal
from urllib.parse import quote

from pydantic import SecretStr, computed_field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    General proj settings
    """
    APP_NAME: str
    DEBUG: bool
    ENVIRONMENT: str
    APP_PORT: int
    API_PREFIX: str

    #  Database settings
    DB_USER: str
    DB_PASSWORD: SecretStr
    DB_NAME: str
    DB_HOST: str
    DB_PORT: int = 5432

    @computed_field
    @property
    def DB_URL(self) -> str:  # noqa: N802
        user = quote(self.DB_USER, safe="")
        password = quote(self.DB_PASSWORD.get_secret_value(), safe="")
        return (
            f"postgresql+asyncpg://{user}:{password}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    # Encrypting
    SECRET_KEY: SecretStr
    JWT_ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int

    # Storage
    STORAGE_BACKEND: Literal["local", "s3"] = "local"
    STORAGE_PATH: str

    # S3 / MinIO
    S3_ENDPOINT_URL: str | None = None
    S3_PUBLIC_ENDPOINT_URL: str | None = None
    S3_BUCKET: str = "autorunning"
    S3_ACCESS_KEY: SecretStr | None = None
    S3_SECRET_KEY: SecretStr | None = None
    S3_REGION: str = "us-east-1"
    S3_PRESIGN_TTL_SECONDS: int = 600
    MINIO_PORT: int = 9000
    MINIO_CONSOLE_PORT: int = 9001

    # RabbitMQ
    RABBITMQ_USER: str
    RABBITMQ_PASSWORD: SecretStr
    RABBITMQ_VHOST: str
    RABBITMQ_HOST: str
    RABBITMQ_PORT: int = 5672

    # Flower
    FLOWER_USER: str
    FLOWER_PASSWORD: SecretStr
    FLOWER_PORT: int = 5555

    # Redis
    REDIS_PASSWORD: SecretStr
    REDIS_HOST: str
    REDIS_PORT: int = 6379
    REDIS_CELERY_DB: int
    REDIS_EVENTS_DB: int

    @computed_field
    @property
    def REDIS_URL(self) -> str:  # noqa: N802
        password = quote(self.REDIS_PASSWORD.get_secret_value(), safe="")
        return f"redis://:{password}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_EVENTS_DB}"

    # Celery
    @computed_field
    @property
    def CELERY_RESULT_BACKEND_URL(self) -> str:  # noqa: N802
        password = quote(self.REDIS_PASSWORD.get_secret_value(), safe="")
        return f"redis://:{password}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_CELERY_DB}"

    @computed_field
    @property
    def CELERY_BROKER_URL(self) -> str:  # noqa: N802
        user = quote(self.RABBITMQ_USER, safe="")
        password = quote(self.RABBITMQ_PASSWORD.get_secret_value(), safe="")
        return (
            f"amqp://{user}:{password}"
            f"@{self.RABBITMQ_HOST}:{self.RABBITMQ_PORT}/{self.RABBITMQ_VHOST}"
        )

    # Websocket
    WS_MAX_CONNECTIONS_PER_USER: int = 5

    # Sweeper
    SWEEPER_ENABLED: bool = True
    SWEEPER_INTERVAL_SECONDS: int = 300
    SWEEPER_STALE_AFTER_SECONDS: int = 900
    SWEEPER_BATCH_LIMIT: int = 100

    # DLQ
    TASK_DELIVERY_LIMIT: int = 5
    DLQ_DRAIN_ENABLED: bool = True
    DLQ_DRAIN_INTERVAL_SECONDS: int = 300
    DLQ_BATCH_LIMIT: int = 50

    @model_validator(mode="after")
    def _guard_sweeper_config(self) -> "Settings":
        if (
            self.SWEEPER_ENABLED
            and self.SWEEPER_STALE_AFTER_SECONDS <= self.SWEEPER_INTERVAL_SECONDS
        ):
            raise ValueError(
                "SWEEPER_STALE_AFTER_SECONDS must exceed SWEEPER_INTERVAL_SECONDS "
                "(recommended: >= 3x) — otherwise the sweeper re-enqueues live tasks"
            )
        return self

    @model_validator(mode="after")
    def _guard_storage_config(self) -> "Settings":
        if self.STORAGE_BACKEND != "s3":
            return self
        missing = [
            name for name, value in (
                ("S3_ACCESS_KEY", self.S3_ACCESS_KEY),
                ("S3_SECRET_KEY", self.S3_SECRET_KEY),
            ) if value is None
        ]
        if missing:
            raise ValueError(f"STORAGE_BACKEND=s3 requires: {', '.join(missing)}")
        return self

    @model_validator(mode="after")
    def _guard_prod_config(self) -> "Settings":
        if self.ENVIRONMENT != "prod":
            return self
        problems: list[str] = []
        if self.DEBUG:
            problems.append("DEBUG must be False in prod")
        if "change-me" in self.SECRET_KEY.get_secret_value().lower() or len(self.SECRET_KEY) < 32:
            problems.append(
                "SECRET_KEY must be a real secret (>= 32 chars, not a CHANGE-ME placeholder)"
            )
        if problems:
            raise ValueError("Unsafe production config: " + "; ".join(problems))
        return self

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings():
    """
    Provides project settings.
    """
    return Settings()
