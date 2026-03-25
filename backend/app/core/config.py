from functools import lru_cache
from pathlib import Path
from uuid import UUID

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(BACKEND_ROOT / ".env"), env_file_encoding="utf-8", extra="ignore")

    app_name: str = "MemoryOS API"
    app_version: str = "0.1.0"
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")
    frontend_origin: str = Field(default="http://localhost:3000", alias="FRONTEND_ORIGIN")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    scheduler_enabled: bool = Field(default=True, alias="SCHEDULER_ENABLED")
    connection_backfill_hour_utc: int = Field(default=2, alias="CONNECTION_BACKFILL_HOUR_UTC")
    topic_maintenance_hour_utc: int = Field(default=3, alias="TOPIC_MAINTENANCE_HOUR_UTC")
    job_user_batch_limit: int = Field(default=100, alias="JOB_USER_BATCH_LIMIT")
    job_memory_batch_limit: int = Field(default=25, alias="JOB_MEMORY_BATCH_LIMIT")
    local_user_id: UUID = Field(default=UUID("00000000-0000-4000-8000-000000000001"), alias="LOCAL_USER_ID")
    local_user_email: str = Field(default="weekend@memoryos.local", alias="LOCAL_USER_EMAIL")

    database_path: str = Field(default="data/memoryos.db", alias="DATABASE_PATH")
    pinecone_api_key: str = Field(default="", alias="PINECONE_API_KEY")
    pinecone_index_host: str = Field(default="", alias="PINECONE_INDEX_HOST")
    pinecone_namespace: str = Field(default="memoryos", alias="PINECONE_NAMESPACE")

    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")

    @property
    def allowed_origins(self) -> list[str]:
        return [self.frontend_origin]


@lru_cache
def get_settings() -> Settings:
    return Settings()
