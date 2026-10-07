from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: Literal["development", "test", "production"] = "development"
    app_name: str = "CV Screening Platform"
    database_url: str = "sqlite:///./cv_screening.db"

    upload_dir: str = "./data/uploads"
    export_dir: str = "./data/exports"
    max_zip_size_mb: int = 200
    max_file_size_mb: int = 20
    max_files_per_zip: int = 500
    analysis_worker_max_workers: int = 2
    status_stream_interval_seconds: float = 1.0
    app_log_level: str = "INFO"
    app_log_file: str = "./data/app.log"
    scoring_mode: Literal["deterministic", "llm_hybrid", "llm_first"] = "llm_first"
    skill_normalization_mode: Literal["dictionary", "ai_assisted"] = "ai_assisted"

    llm_backend: Literal["mock", "azure"] = "mock"
    llm_provider: Literal["mock", "azure_openai"] = "mock"
    azure_openai_endpoint: str = ""
    azure_openai_api_key: str = ""
    azure_openai_chat_deployment: str = ""
    azure_openai_deployment: str = ""
    azure_openai_embedding_deployment: str = ""
    azure_openai_api_version: str = ""

    document_intelligence_provider: Literal["local", "azure_document_intelligence"] = "local"
    azure_document_intelligence_endpoint: str = ""
    azure_document_intelligence_key: str = ""
    azure_document_intelligence_api_version: str = "2024-11-30"
    azure_document_intelligence_model_id: str = "prebuilt-layout"

    enable_ocr: bool = Field(default=True, alias="ENABLE_OCR")

    @property
    def max_zip_size_bytes(self) -> int:
        return self.max_zip_size_mb * 1024 * 1024

    @property
    def max_file_size_bytes(self) -> int:
        return self.max_file_size_mb * 1024 * 1024

    def ensure_directories(self) -> None:
        Path(self.upload_dir).mkdir(parents=True, exist_ok=True)
        Path(self.export_dir).mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_directories()
    return settings
