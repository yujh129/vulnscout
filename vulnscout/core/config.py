from __future__ import annotations

from enum import Enum
from pathlib import Path

from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class ModelBackend(str, Enum):
    LLAMA_CPP = "llama.cpp"
    VLLM = "vllm"
    OPENAI_COMPATIBLE = "openai-compatible"


class Settings(BaseSettings):
    model_name: str = "deepseek-coder-1.3b-instruct"
    model_backend: ModelBackend = ModelBackend.LLAMA_CPP
    openai_base_url: str = "http://localhost:8000/v1"
    openai_api_key: str = "not-needed"

    database_url: str = "sqlite:///vulnscout.db"
    model_cache_dir: str = str(Path.home() / ".vulnscout" / "models")

    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/0"

    max_file_size: int = 1024 * 1024  # 1MB
    max_upload_size: int = 100 * 1024 * 1024  # 100MB
    chunk_timeout: int = 30  # seconds per chunk
    max_concurrent_chunks: int = 4

    language: str = "en"

    @property
    def model_path(self) -> Path:
        return Path(self.model_cache_dir) / self.model_name

    model_config = ConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
