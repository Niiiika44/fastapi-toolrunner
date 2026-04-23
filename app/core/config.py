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
    DB_URL: str

    RABBITMQ_URL: str

    API_PREFIX: str

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
