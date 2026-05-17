from __future__ import annotations

from enum import Enum
from pathlib import Path

from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class ModelBackend(str, Enum):
    OLLAMA = "ollama"
    LLAMA_CPP = "llama.cpp"
    VLLM = "vllm"
    OPENAI_COMPATIBLE = "openai-compatible"


class Settings(BaseSettings):
    model_name: str = "deepseek-coder:1.3b"
    model_backend: ModelBackend = ModelBackend.LLAMA_CPP
    openai_base_url: str = "http://localhost:11434/v1"
    openai_api_key: str = "not-needed"

    database_url: str = "sqlite:///vulnscout.db"
    model_cache_dir: str = str(Path.home() / ".vulnscout" / "models")

    ollama_api_url: str = "http://localhost:11434"

    max_file_size: int = 1024 * 1024  # 1MB
    max_upload_size: int = 100 * 1024 * 1024  # 100MB
    chunk_timeout: int = 30  # seconds per chunk
    max_concurrent_chunks: int = 4

    language: str = "en"

    # GitHub integration
    github_token: str = ""

    # model_name is the Ollama tag, e.g. deepseek-coder:1.3b

    model_config = ConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
