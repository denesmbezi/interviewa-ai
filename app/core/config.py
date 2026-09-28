from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    app_name: str = "Interviewa AI"
    database_url: str = "sqlite:///./interviewa.db"
    secret_key: str = "change-me-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    assemblyai_api_key: str = ""
    assemblyai_api_base_url: str = "https://agents.assemblyai.com"
    session_cookie_name: str = "interviewa_session"
    cors_origins: str = "http://localhost:8000,http://127.0.0.1:8000"

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")


@lru_cache()
def get_settings() -> Settings:
    return Settings()
