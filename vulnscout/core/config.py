from __future__ import annotations

from enum import Enum
from pathlib import Path

from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class ModelProvider(str, Enum):
    OLLAMA = "ollama"
    OPENAI = "openai"
    CUSTOM = "custom"


class Settings(BaseSettings):
    model_provider: ModelProvider = ModelProvider.OLLAMA
    model_name: str = "deepseek-coder:1.3b"
    openai_base_url: str = "https://api.openai.com/v1"
    openai_api_key: str = ""
    ollama_api_url: str = "http://localhost:11434"
    database_url: str = "sqlite:///vulnscout.db"
    model_cache_dir: str = str(Path.home() / ".vulnscout" / "models")
    max_file_size: int = 1024 * 1024
    max_upload_size: int = 100 * 1024 * 1024
    chunk_timeout: int = 30
    max_concurrent_chunks: int = 4
    language: str = "en"
    github_token: str = ""
    # Model inference parameters
    ai_temperature: float = 0.1
    ai_max_tokens_analyze: int = 1024
    ai_max_tokens_fix: int = 4096

    model_config = ConfigDict(env_file=".env", env_file_encoding="utf-8")

    def reload(self) -> Settings:
        """Hot-reload settings from .env file without restarting the server."""
        new = Settings(_env_file=".env", _env_file_encoding="utf-8")
        for field in self.model_fields:
            setattr(self, field, getattr(new, field))
        return self

    @property
    def is_ollama(self) -> bool:
        return self.model_provider == ModelProvider.OLLAMA

    @property
    def is_cloud(self) -> bool:
        return self.model_provider in (ModelProvider.OPENAI, ModelProvider.CUSTOM)


settings = Settings()
