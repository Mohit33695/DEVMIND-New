"""
LLM Provider Abstraction, Mock Provider Implementation, & Provider Factory.

Purpose:
Defines the LLMProvider interface for generating grounded codebase answers,
implements MockLLMProvider for offline development/testing, and exposes a factory
function for environment-based provider resolution.
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from pydantic import BaseModel

from app.core.config import UnsupportedProviderError, get_settings
from app.schemas.chat import ChatMessage


# -----------------------------------------------------------------------------
# Domain Exceptions for LLM Providers
# -----------------------------------------------------------------------------
class LLMProviderError(Exception):
    """Base domain exception for LLM completion provider errors."""

    pass


class LLMAuthError(LLMProviderError):
    """Raised when provider authentication fails (HTTP 401)."""

    pass


class LLMRateLimitError(LLMProviderError):
    """Raised when provider rate limits are exceeded (HTTP 429)."""

    pass


class LLMNetworkError(LLMProviderError):
    """Raised on socket/transport network failure."""

    pass


class LLMTimeoutError(LLMProviderError):
    """Raised when an LLM HTTP completion request times out."""

    pass


class LLMResponseError(LLMProviderError):
    """Raised when provider response structure or status code is invalid."""

    pass


class LLMResponse(BaseModel):
    """Container for generated LLM text and provider metadata."""

    content: str
    answer: str
    provider_name: str
    model_name: str
    grounded: bool = True


class LLMProvider(ABC):
    """Abstract interface for LLM completion providers."""

    @abstractmethod
    def generate_response(
        self,
        system_instruction: str,
        user_message: str,
        grounded_context: str,
        history: List[ChatMessage] = [],
    ) -> LLMResponse:
        """
        Generates a grounded completion based on system prompts and codebase context.

        Args:
            system_instruction: Core AI system prompt boundary.
            user_message: Developer's query text.
            grounded_context: Formatted untrusted repository code chunks.
            history: Optional conversation message history.

        Returns:
            LLMResponse: Grounded text completion and metadata.
        """
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        """Returns readable provider name identifier."""
        pass


class MockLLMProvider(LLMProvider):
    """Deterministic offline mock provider for local development and unit tests."""

    PROVIDER_NAME = "MockLLMProvider (Development/Test Mode)"
    MODEL_NAME = "mock-codebase-engine-v1"

    def get_provider_name(self) -> str:
        return self.PROVIDER_NAME

    def generate_response(
        self,
        system_instruction: str,
        user_message: str,
        grounded_context: str,
        history: List[ChatMessage] = [],
    ) -> LLMResponse:
        """
        Generates deterministic grounded answers or explicit insufficient evidence messages.
        """
        clean_context = (grounded_context or "").strip()

        if not clean_context:
            insufficient_text = (
                "Based on the indexed repository evidence available to DevMind AI, "
                "there is insufficient evidence to answer this question. "
                "Try re-indexing the repository or searching for specific file names or symbol signatures."
            )
            return LLMResponse(
                content=insufficient_text,
                answer=insufficient_text,
                provider_name=self.PROVIDER_NAME,
                model_name=self.MODEL_NAME,
                grounded=False,
            )

        # Context exists - build deterministic grounded analysis summary
        lines = [
            f"### DevMind AI Grounded Analysis ({self.PROVIDER_NAME})",
            f"**Query:** {user_message}",
            "",
            "Based on the retrieved repository evidence, the following code structures were identified:",
            "",
        ]

        # Parse snippet headers from formatted context string if available
        context_blocks = clean_context.split("---")
        block_count = 0
        for block in context_blocks:
            sublines = [line.strip() for line in block.strip().split("\n") if line.strip()]
            if sublines:
                block_count += 1
                header_info = sublines[0]
                lines.append(f"- **Chunk {block_count}:** {header_info}")

        lines.extend([
            "",
            "**Context Summary:**",
            f"Analyzed {block_count} relevant codebase context block(s) retrieved from stored repository files.",
            "All cited line ranges and symbol definitions have been verified from static repository source code.",
        ])

        final_answer = "\n".join(lines)

        return LLMResponse(
            content=final_answer,
            answer=final_answer,
            provider_name=self.PROVIDER_NAME,
            model_name=self.MODEL_NAME,
            grounded=True,
        )


def get_llm_provider(provider_name: Optional[str] = None) -> LLMProvider:
    """
    Factory function instantiating the requested or configured LLMProvider.

    Args:
        provider_name: Optional provider identifier override (e.g. 'mock', 'openai').

    Returns:
        LLMProvider: An initialized LLM provider instance.

    Raises:
        UnsupportedProviderError: If the requested provider is unknown or missing required API keys.
    """
    settings = get_settings()
    name = (provider_name or settings.LLM_PROVIDER).strip().lower()

    if name == "mock":
        return MockLLMProvider()

    if name == "openai":
        if not settings.OPENAI_API_KEY or not settings.OPENAI_API_KEY.strip():
            raise UnsupportedProviderError(
                "LLM_PROVIDER is set to 'openai', but OPENAI_API_KEY is not configured."
            )
        from app.services.providers.openai_llm import OpenAILLMProvider

        return OpenAILLMProvider(
            api_key=settings.OPENAI_API_KEY,
            model=settings.LLM_MODEL,
            timeout=settings.LLM_TIMEOUT_SECONDS,
            max_tokens=settings.LLM_MAX_TOKENS,
            base_url=settings.LLM_API_BASE_URL,
        )

    raise UnsupportedProviderError(
        f"Unsupported LLM provider: '{name}'. Currently supported providers: ['mock', 'openai']."
    )
