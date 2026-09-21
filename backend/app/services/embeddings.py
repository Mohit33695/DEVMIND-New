"""
Embedding Provider Abstraction & Provider Factory.

Purpose:
Provides a pluggable interface for vector embedding generation, supporting
deterministic local mock embeddings for testing/offline development and optional
future production embedding models (e.g. SentenceTransformers, OpenAI).
"""

from abc import ABC, abstractmethod
import hashlib
import math
from typing import List, Optional

from app.core.config import UnsupportedProviderError, get_settings


# -----------------------------------------------------------------------------
# Domain Exceptions for Embedding Providers
# -----------------------------------------------------------------------------
class EmbeddingProviderError(Exception):
    """Base domain exception for embedding provider errors."""

    pass


class EmbeddingAuthError(EmbeddingProviderError):
    """Raised when provider authentication fails (HTTP 401)."""

    pass


class EmbeddingRateLimitError(EmbeddingProviderError):
    """Raised when provider rate limits are exceeded (HTTP 429)."""

    pass


class EmbeddingNetworkError(EmbeddingProviderError):
    """Raised on socket/transport network failure."""

    pass


class EmbeddingTimeoutError(EmbeddingProviderError):
    """Raised when an embedding HTTP request times out."""

    pass


class EmbeddingResponseError(EmbeddingProviderError):
    """Raised when provider response structure or status code is invalid."""

    pass


class EmbeddingDimensionMismatchError(EmbeddingProviderError):
    """Raised when returned vector dimension does not match configured dimension."""

    pass


class EmbeddingProvider(ABC):
    """Abstract Base Class for vector embedding models."""

    @abstractmethod
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        Generates vector embeddings for a list of text strings.

        Args:
            texts: List of text content to embed.

        Returns:
            List[List[float]]: List of normalized float vector arrays.
        """
        pass

    @abstractmethod
    def get_dimension(self) -> int:
        """Returns the embedding vector dimension."""
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        """Returns the human-readable provider identifier."""
        pass


class MockEmbeddingProvider(EmbeddingProvider):
    """
    Deterministic mock embedding provider for testing and local development.
    Uses pure Python text hashing to create pseudo-semantic unit vectors without network/API dependencies.
    """

    DIMENSION = 384

    def __init__(self, dimension: int = 384):
        self.dimension = dimension

    def get_dimension(self) -> int:
        return self.dimension

    def get_provider_name(self) -> str:
        return "MockEmbeddingProvider (Development/Test Mode)"

    def _hash_word_to_vector(self, text: str) -> List[float]:
        """Maps input text deterministically to a normalized pseudo-vector in pure Python."""
        vec = [0.0] * self.dimension

        if not text or not text.strip():
            return vec

        import re
        # Split on non-alphanumeric characters (keeping underscores)
        raw_words = re.findall(r'[a-zA-Z0-9_]+', text.lower())
        tokens = []
        for w in raw_words:
            tokens.append(w)
            if "_" in w:
                subparts = [p for p in w.split("_") if len(p) >= 2]
                tokens.extend(subparts)

        if not tokens:
            return vec

        for token in tokens:
            # Generate MD5 hash bytes for token
            h_bytes = hashlib.md5(token.encode("utf-8")).digest()
            for i, byte_val in enumerate(h_bytes):
                idx = (i * 24 + byte_val) % self.dimension
                val = (byte_val - 128) / 128.0
                vec[idx] += val

        # Normalize vector to unit length for cosine similarity calculations
        sq_sum = sum(x * x for x in vec)
        if sq_sum > 1e-9:
            norm = math.sqrt(sq_sum)
            vec = [x / norm for x in vec]

        return vec

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Embeds a list of texts into deterministic normalized pseudo-vectors."""
        return [self._hash_word_to_vector(t) for t in texts]


def get_embedding_provider(provider_name: Optional[str] = None) -> EmbeddingProvider:
    """
    Factory function instantiating the requested or configured EmbeddingProvider.

    Args:
        provider_name: Optional provider identifier override (e.g. 'mock', 'openai').

    Returns:
        EmbeddingProvider: An initialized embedding provider instance.

    Raises:
        UnsupportedProviderError: If the requested provider is unknown or missing required API keys.
    """
    settings = get_settings()
    name = (provider_name or settings.EMBEDDING_PROVIDER).strip().lower()

    if name == "mock":
        return MockEmbeddingProvider(dimension=settings.EMBEDDING_DIMENSION)

    if name == "openai":
        if not settings.OPENAI_API_KEY or not settings.OPENAI_API_KEY.strip():
            raise UnsupportedProviderError(
                "EMBEDDING_PROVIDER is set to 'openai', but OPENAI_API_KEY is not configured."
            )
        from app.services.providers.openai_embedding import OpenAIEmbeddingProvider

        return OpenAIEmbeddingProvider(
            api_key=settings.OPENAI_API_KEY,
            model=settings.EMBEDDING_MODEL,
            dimension=settings.EMBEDDING_DIMENSION,
            timeout=settings.EMBEDDING_TIMEOUT_SECONDS,
            batch_size=settings.EMBEDDING_BATCH_SIZE,
            base_url=settings.EMBEDDING_API_BASE_URL,
        )

    raise UnsupportedProviderError(
        f"Unsupported embedding provider: '{name}'. Currently supported providers: ['mock', 'openai']."
    )
