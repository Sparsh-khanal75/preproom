"""Runtime configuration from environment variables (12-factor)."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    env: Literal["dev", "test", "prod"] = "dev"
    database_url: str = "postgresql+asyncpg://preproom:preproom@localhost:5432/preproom"
    jwt_secret: str = Field(default="dev-only-change-me-please-32-bytes-min", min_length=32)
    access_token_minutes: int = 60 * 12
    cookie_secure: bool = False
    cors_origins: list[str] = ["http://localhost:3000"]

    # AI providers - all free by default
    llm_provider: Literal["ollama", "openai_compatible", "mock"] = "mock"
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:7b"
    openai_base_url: str = "https://api.groq.com/openai/v1"
    openai_api_key: str | None = None
    openai_model: str = "llama-3.1-8b-instant"
    llm_timeout: float = 120.0

    stt_provider: Literal["whisper", "mock"] = "mock"
    whisper_model: str = "small"

    upload_dir: str = "./data/uploads"
    max_audio_bytes: int = 10 * 1024 * 1024
    max_answer_chars: int = 5000
    run_jobs_inline: bool = False  # tests: execute jobs immediately instead of via the worker
    packs_dir: str | None = None  # extra packs folder in addition to the built-in ones


@lru_cache
def get_settings() -> Settings:
    return Settings()
