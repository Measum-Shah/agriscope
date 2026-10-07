"""Configuration settings loaded from environment variables."""

from typing import List, Union

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # General
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    APP_NAME: str = "AgriScope"
    API_V1_PREFIX: str = "/api/v1"
    SECRET_KEY: str = "default_insecure_development_secret_key_12345"
    ALLOWED_ORIGINS: Union[str, List[str]] = ["http://localhost:5173", "http://localhost:3000"]
    REQUEST_TIMEOUT_SECONDS: int = 60

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return v
        return ["*"]

    # Database
    POSTGRES_HOST: str = "postgres"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "agriscope"
    POSTGRES_USER: str = "agriscope_user"
    POSTGRES_PASSWORD: str = "agriscope_dev_password"
    DATABASE_URL: str = (
        "postgresql+asyncpg://agriscope_user:agriscope_dev_password@postgres:5432/agriscope"
    )

    # Redis & Celery
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ""
    REDIS_DB: int = 0
    REDIS_URL: str = "redis://redis:6379/0"
    CELERY_BROKER_URL: str = "redis://redis:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/2"

    # MinIO
    MINIO_ROOT_USER: str = "minioadmin"
    MINIO_ROOT_PASSWORD: str = "minioadmin"
    MINIO_ENDPOINT: str = "minio:9000"
    MINIO_PORT: int = 9000
    MINIO_CONSOLE_PORT: int = 9001
    MINIO_USE_SSL: bool = False
    MINIO_DEFAULT_BUCKET: str = "agriscope-bucket"
    STORAGE_PROVIDER: str = "mock"

    # ML
    ML_SERVICE_URL: str = "http://ml-service:8001"
    DEFAULT_MODEL_VERSION: str = "v1.0.0"

    # Providers
    WEATHER_PROVIDER: str = "mock"
    SATELLITE_PROVIDER: str = "mock"
    BILLING_PROVIDER: str = "mock"
    EMAIL_PROVIDER: str = "mock"
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_PRICE_ID_PRO: str = "price_pro_monthly"

    # Auth
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    COOKIE_SECURE: bool = False
    COOKIE_SAMESITE: str = "lax"
    BCRYPT_ROUNDS: int = 12
    MAX_LOGIN_ATTEMPTS: int = 5
    LOCKOUT_DURATION_MINUTES: int = 15

    # Observability
    PROMETHEUS_METRICS_ENABLED: bool = True
    SENTRY_DSN: str = ""
    LOG_LEVEL: str = "INFO"


settings = Settings()
