from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    General proj settings
    """
    APP_NAME: str
    DEBUG: bool
    ENVIRONMENT: str

    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_HOST: str
    POSTGRES_PORT: int = 5432

    DATABASE_URL: str
    RABBITMQ_URL: str

    API_PREFIX: str

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
