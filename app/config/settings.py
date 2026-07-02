"""
Configurações do sistema (Pydantic Settings).
"""
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    environment: str = "development"
    database_url: str = Field(..., env="DATABASE_URL")
    redis_url: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    openai_api_key: str = Field(..., env="OPENAI_API_KEY")
    google_places_api_key: str = Field(..., env="GOOGLE_PLACES_API_KEY")
    secret_key: str = Field(..., env="SECRET_KEY")
    max_daily_emails: int = 50
    score_threshold: int = 70

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
