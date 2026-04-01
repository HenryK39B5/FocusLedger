from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env", "../../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "FocusLedger"
    environment: str = "development"
    api_prefix: str = "/api/v1"
    database_url: str = "postgresql+psycopg://focusledger:focusledger@localhost:5432/focusledger"
    redis_url: str = "redis://localhost:6379/0"
    allow_cors_origins: str = "http://localhost:3000,http://localhost:3300"
    auto_create_schema: bool = True
    article_storage_path: str = "data/articles"
    llm_provider: str = "rule"
    openai_api_key: str = ""
    openai_model: str = "gpt-4.1-mini"
    openai_base_url: str = "https://api.openai.com/v1"
    openai_organization: str = ""
    openai_verify_ssl: bool = True
    openai_temperature: float = 0.2
    openai_timeout_seconds: int = 45
    openai_max_retries: int = 2
    wechat_verify_ssl: bool = False
    request_timeout_seconds: int = 20
    embed_dimension: int = 256
    qclaw_integration_key: str = ""
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"

    @property
    def cors_origins(self) -> list[str]:
        return [item.strip() for item in self.allow_cors_origins.split(",") if item.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
