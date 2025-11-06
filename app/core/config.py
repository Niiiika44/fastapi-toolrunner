from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    APP_NAME: str = Field("AutoRunning", description="Name of the app")
    DEBUG: bool = Field(True, description="Mode to run")
    API_PREFIX: str = Field("/api", description="Base prefix for all routes")
    DATABASE_URL: str = Field(
        "postgresql+asyncpg://user:password@localhost:5432/autorunning",
        description="Database connection URL"
    )
    RABBITMQ_URL: str = Field(
        "amqp://guest:guest@localhost/",
        description="RabbitMQ connection URL"
    )
    ENVIRONMENT: str = Field("development", description="Environment: development/production/test")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
