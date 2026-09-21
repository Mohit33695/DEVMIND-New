"""
Centralized AI & Application Configuration.

Purpose:
Provides environment-driven configuration for DevMind AI services, embedding providers,
and LLM completion models with zero-secret default fallbacks for local development and testing.
"""

import os
from typing import Optional
from pydantic.v1 import BaseSettings, validator


class UnsupportedProviderError(ValueError):
    """Raised when an unsupported or unconfigured AI provider is requested."""

    pass


class Settings(BaseSettings):
    """Application settings with environment variable overrides."""

    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"

    # Embedding Provider Configuration
    EMBEDDING_PROVIDER: str = "mock"
    EMBEDDING_MODEL: str = "mock"
    EMBEDDING_DIMENSION: int = 384
    EMBEDDING_API_BASE_URL: str = "https://api.openai.com/v1"
    EMBEDDING_TIMEOUT_SECONDS: int = 30
    EMBEDDING_BATCH_SIZE: int = 100

    # LLM Provider Configuration
    LLM_PROVIDER: str = "mock"
    LLM_MODEL: str = "mock"
    LLM_API_BASE_URL: str = "https://api.openai.com/v1"
    LLM_TIMEOUT_SECONDS: int = 30
    LLM_MAX_TOKENS: int = 1024

    # Backend Secret Keys (Backend-only, optional, default None)
    OPENAI_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None

    @validator(
        "EMBEDDING_TIMEOUT_SECONDS",
        "EMBEDDING_BATCH_SIZE",
        "EMBEDDING_DIMENSION",
        "LLM_TIMEOUT_SECONDS",
        "LLM_MAX_TOKENS",
    )
    def validate_positive_int(cls, v, field):
        if v <= 0:
            raise ValueError(f"{field.name} must be greater than 0")
        return v

    class Config:
        case_sensitive = False
        env_file = ".env"
        env_file_encoding = "utf-8"


def get_settings() -> Settings:
    """Returns a fresh Settings instance reading from active environment variables."""
    return Settings()


# Global singleton settings instance for default service usage
settings = get_settings()
