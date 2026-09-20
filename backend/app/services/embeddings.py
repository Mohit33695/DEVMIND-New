"""
Embedding Provider Abstraction.

Purpose:
Provides a pluggable interface for vector embedding generation, supporting
deterministic local mock embeddings for testing/offline development and optional
future production embedding models (e.g. SentenceTransformers, OpenAI).
"""

from abc import ABC, abstractmethod
import hashlib
import math
from typing import List


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

        # Split into lowercase tokens
        tokens = text.lower().split()
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
