"""
Unit Tests for Centralized AI Configuration & Provider Factories (Milestone AA.1).
"""

import os
import pytest
from app.core.config import Settings, UnsupportedProviderError, get_settings
from app.services.embeddings import (
    EmbeddingProvider,
    MockEmbeddingProvider,
    get_embedding_provider,
)
from app.services.llm import (
    LLMProvider,
    MockLLMProvider,
    get_llm_provider,
)
from app.services.rag import CodebaseRAGService
from app.services.chat import CodebaseChatService


# -----------------------------------------------------------------------------
# 1. Default Configuration Tests
# -----------------------------------------------------------------------------
def test_default_config_values():
    s = Settings()
    assert s.ENVIRONMENT == "development"
    assert s.LOG_LEVEL == "INFO"
    assert s.EMBEDDING_PROVIDER == "mock"
    assert s.EMBEDDING_MODEL == "mock"
    assert s.EMBEDDING_DIMENSION == 384
    assert s.LLM_PROVIDER == "mock"
    assert s.LLM_MODEL == "mock"
    assert s.LLM_TIMEOUT_SECONDS == 30
    assert s.LLM_MAX_TOKENS == 1024
    assert s.OPENAI_API_KEY is None


def test_default_embedding_factory_returns_mock():
    provider = get_embedding_provider()
    assert isinstance(provider, EmbeddingProvider)
    assert isinstance(provider, MockEmbeddingProvider)
    assert provider.get_dimension() == 384
    assert "MockEmbeddingProvider" in provider.get_provider_name()


def test_default_llm_factory_returns_mock():
    provider = get_llm_provider()
    assert isinstance(provider, LLMProvider)
    assert isinstance(provider, MockLLMProvider)
    assert "MockLLMProvider" in provider.get_provider_name()


# -----------------------------------------------------------------------------
# 2. Explicit Provider Selection Tests
# -----------------------------------------------------------------------------
def test_explicit_mock_embedding_provider():
    provider = get_embedding_provider("mock")
    assert isinstance(provider, MockEmbeddingProvider)
    assert provider.get_dimension() == 384


def test_explicit_mock_llm_provider():
    provider = get_llm_provider("mock")
    assert isinstance(provider, MockLLMProvider)


# -----------------------------------------------------------------------------
# 3. Unsupported Provider Error Handling Tests
# -----------------------------------------------------------------------------
def test_unsupported_embedding_provider_raises_error():
    with pytest.raises(UnsupportedProviderError) as exc_info:
        get_embedding_provider("unsupported_provider")
    assert "Unsupported embedding provider: 'unsupported_provider'" in str(exc_info.value)
    assert "mock" in str(exc_info.value)


def test_unsupported_llm_provider_raises_error():
    with pytest.raises(UnsupportedProviderError) as exc_info:
        get_llm_provider("anthropic")
    assert "Unsupported LLM provider: 'anthropic'" in str(exc_info.value)
    assert "mock" in str(exc_info.value)


# -----------------------------------------------------------------------------
# 4. Environment Override Tests
# -----------------------------------------------------------------------------
def test_environment_override_embedding_provider(monkeypatch):
    monkeypatch.setenv("EMBEDDING_PROVIDER", "invalid_provider")
    with pytest.raises(UnsupportedProviderError) as exc_info:
        get_embedding_provider()
    assert "Unsupported embedding provider: 'invalid_provider'" in str(exc_info.value)


def test_environment_override_llm_provider(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "unsupported_llm")
    with pytest.raises(UnsupportedProviderError) as exc_info:
        get_llm_provider()
    assert "Unsupported LLM provider: 'unsupported_llm'" in str(exc_info.value)


# -----------------------------------------------------------------------------
# 5. Service Wiring Verification
# -----------------------------------------------------------------------------
def test_rag_service_uses_embedding_factory():
    rag_provider = CodebaseRAGService.get_embedding_provider()
    assert isinstance(rag_provider, MockEmbeddingProvider)


def test_chat_service_uses_llm_factory(monkeypatch):
    # Ensure reset of overridden provider if any
    monkeypatch.setattr(CodebaseChatService, "_llm_provider", None)
    chat_provider = CodebaseChatService.get_llm_provider()
    assert isinstance(chat_provider, MockLLMProvider)
