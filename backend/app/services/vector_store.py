"""
Vector Store Service.

Purpose:
Manages vector storage and repository-isolated semantic retrieval.
Uses a pure Python in-memory vector index with exact cosine similarity matching,
guaranteeing zero cross-repository retrieval leakage without external database dependencies.
"""

from abc import ABC, abstractmethod
import math
from typing import Any, Dict, List, Optional, Tuple

from app.schemas.rag import CodeChunk


class VectorStore(ABC):
    """Abstract interface for vector database storage."""

    @abstractmethod
    def add_chunks(
        self, repo_id: str, chunks: List[CodeChunk], embeddings: List[List[float]]
    ) -> None:
        """Stores chunks and corresponding vector embeddings."""
        pass

    @abstractmethod
    def search(
        self,
        repo_id: str,
        query_vector: List[float],
        top_k: int = 5,
        score_threshold: float = 0.0,
    ) -> List[Tuple[CodeChunk, float]]:
        """Executes repository-scoped vector search."""
        pass

    @abstractmethod
    def delete_repository_vectors(self, repo_id: str) -> None:
        """Deletes all vectors and chunks stored for a repository."""
        pass

    @abstractmethod
    def has_repository(self, repo_id: str) -> bool:
        """Checks whether a repository has been indexed."""
        pass

    @abstractmethod
    def get_repository_chunk_count(self, repo_id: str) -> int:
        """Returns total chunks indexed for a repository."""
        pass

    @abstractmethod
    def set_repository_metadata(
        self, repo_id: str, provider: str, model: str, dimension: int
    ) -> None:
        """Stores index metadata for a repository."""
        pass

    @abstractmethod
    def get_repository_metadata(self, repo_id: str) -> Optional[Dict[str, Any]]:
        """Returns index metadata for a repository if present."""
        pass


class InMemoryVectorStore(VectorStore):
    """
    Pure Python in-memory vector store implementation.
    Maintains strict repository isolation by partitioning storage by repo_id.
    """

    def __init__(self):
        # Maps repo_id -> List[Tuple[CodeChunk, List[float]]]
        self._storage: Dict[str, List[Tuple[CodeChunk, List[float]]]] = {}
        # Maps repo_id -> Dict[str, Any] metadata
        self._metadata: Dict[str, Dict[str, Any]] = {}

    @staticmethod
    def _cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
        """Computes cosine similarity between two float vectors in pure Python."""
        if not vec_a or not vec_b or len(vec_a) != len(vec_b):
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
        norm_a = sum(a * a for a in vec_a)
        norm_b = sum(b * b for b in vec_b)

        if norm_a <= 1e-9 or norm_b <= 1e-9:
            return 0.0

        return dot_product / (math.sqrt(norm_a) * math.sqrt(norm_b))

    def add_chunks(
        self, repo_id: str, chunks: List[CodeChunk], embeddings: List[List[float]]
    ) -> None:
        """Stores chunks and embeddings under repo_id partition."""
        if repo_id not in self._storage:
            self._storage[repo_id] = []

        for chunk, emb in zip(chunks, embeddings):
            # Enforce repository ID match on metadata
            if chunk.repo_id == repo_id:
                self._storage[repo_id].append((chunk, emb))

    def search(
        self,
        repo_id: str,
        query_vector: List[float],
        top_k: int = 5,
        score_threshold: float = 0.0,
    ) -> List[Tuple[CodeChunk, float]]:
        """
        Executes vector similarity search strictly scoped to the requested repo_id.
        Guarantee: Chunks belonging to other repo_ids are never inspected or returned.
        """
        if not repo_id or repo_id not in self._storage:
            return []

        # STRICT REPOSITORY BOUNDARY ISOLATION
        repo_items = self._storage[repo_id]

        scored_results: List[Tuple[CodeChunk, float]] = []
        for chunk, emb in repo_items:
            # Double check repository boundary
            if chunk.repo_id != repo_id:
                continue

            score = self._cosine_similarity(query_vector, emb)
            if score >= score_threshold:
                scored_results.append((chunk, round(score, 4)))

        # Sort by similarity score descending, then chunk_id ascending
        scored_results.sort(key=lambda x: (-x[1], x[0].chunk_id))

        # Return top_k
        return scored_results[:top_k]

    def delete_repository_vectors(self, repo_id: str) -> None:
        """Removes all stored chunks, vectors, and metadata for repo_id."""
        if repo_id in self._storage:
            del self._storage[repo_id]
        if repo_id in self._metadata:
            del self._metadata[repo_id]

    def has_repository(self, repo_id: str) -> bool:
        """Returns True if repo_id has indexed vectors."""
        return repo_id in self._storage and len(self._storage[repo_id]) > 0

    def get_repository_chunk_count(self, repo_id: str) -> int:
        """Returns number of chunks indexed for repo_id."""
        if repo_id in self._storage:
            return len(self._storage[repo_id])
        return 0

    def set_repository_metadata(
        self, repo_id: str, provider: str, model: str, dimension: int
    ) -> None:
        """Stores index metadata for a repository."""
        self._metadata[repo_id] = {
            "provider": provider,
            "model": model,
            "dimension": dimension,
        }

    def get_repository_metadata(self, repo_id: str) -> Optional[Dict[str, Any]]:
        """Returns index metadata for a repository if present."""
        return self._metadata.get(repo_id)


# Global singleton instance of vector store for in-memory service persistence
global_vector_store = InMemoryVectorStore()
