# app/core/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "DocTime API"
    APP_VERSION: str = "1.0.0"

    # این مقادیر از فایل .env خوانده می‌شوند؛ در غیر این صورت از مقادیر پیش‌فرض استفاده می‌شود.
    SECRET_KEY: str = "change-this-in-production-very-secure-key-12345"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours (60 * 24)

    DATABASE_URL: str = "sqlite:///./doctime.db"

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


settings = Settings()
