from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    APP_NAME: str = Field("AutoRunning", description="Название приложения")
    DEBUG: bool = Field(True, description="Режим отладки")
    API_PREFIX: str = Field("/api", description="Базовый префикс для всех маршрутов")
    DATABASE_URL: str = Field(
        "postgresql+asyncpg://user:password@localhost:5432/autorunning",
        description="URL для подключения к базе данных"
    )
    RABBITMQ_URL: str = Field(
        "amqp://guest:guest@localhost/",
        description="Подключение к RabbitMQ"
    )
    ENVIRONMENT: str = Field("development", description="Окружение: development/production/test")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
