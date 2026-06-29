from functools import lru_cache

from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    General proj settings
    """
    APP_NAME: str
    DEBUG: bool
    ENVIRONMENT: str

    #  Database settings
    DB_USER: str
    DB_PASSWORD: str
    DB_NAME: str
    DB_HOST: str
    DB_PORT: int = 5432

    @computed_field
    @property
    def DB_URL(self) -> str:  # noqa: N802
        return (
            f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    # Encrypting
    SECRET_KEY: str
    JWT_ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int

    # Storage
    STORAGE_PATH: str

    # RabbitMQ
    RABBITMQ_USER: str
    RABBITMQ_PASSWORD: str
    RABBITMQ_VHOST: str
    RABBITMQ_HOST: str
    RABBITMQ_PORT: int = 5672

    # Flower
    FLOWER_USER: str
    FLOWER_PASSWORD: str
    FLOWER_PORT: int = 5555

    # Celery
    CELERY_BACKEND_HOST: str
    CELERY_BACKEND_PORT: int = 6379
    CELERY_BACKEND_NUM: int

    @computed_field
    @property
    def CELERY_RESULT_BACKEND_URL(self) -> str:  # noqa: N802
        return f"redis://{self.CELERY_BACKEND_HOST}:{self.CELERY_BACKEND_PORT}/{self.CELERY_BACKEND_NUM}"

    @computed_field
    @property
    def CELERY_BROKER_URL(self) -> str:  # noqa: N802
        return (
            f"amqp://{self.RABBITMQ_USER}:{self.RABBITMQ_PASSWORD}"
            f"@{self.RABBITMQ_HOST}:{self.RABBITMQ_PORT}/{self.RABBITMQ_VHOST}"
        )

    API_PREFIX: str

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings():
    """
    Provides project settings.
    """
    return Settings()
