"""
Vector Store Service.

Purpose:
Manages vector storage and repository-isolated semantic retrieval.
Uses a pure Python in-memory vector index with exact cosine similarity matching,
guaranteeing zero cross-repository retrieval leakage without external database dependencies.
"""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
import json
import logging
import math
import os
import threading
from typing import Any, Dict, List, Optional, Tuple

from app.schemas.rag import CodeChunk
from app.services.storage import RepositoryStorageService

logger = logging.getLogger(__name__)


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


class PersistentVectorStore(VectorStore):
    """
    Local file-backed persistent vector store implementation.
    Persists vectors, chunks, and metadata under backend/storage/repositories/{repo_id}/index.json.
    Guarantees repository isolation, thread safety via per-repo locks, and atomic disk writes.
    """

    INDEX_FILENAME = "index.json"

    def __init__(self, base_storage_dir: Optional[str] = None):
        self.base_storage_dir = base_storage_dir or RepositoryStorageService.BASE_STORAGE_DIR
        # Maps repo_id -> List[Tuple[CodeChunk, List[float]]]
        self._storage: Dict[str, List[Tuple[CodeChunk, List[float]]]] = {}
        # Maps repo_id -> Dict[str, Any] metadata
        self._metadata: Dict[str, Dict[str, Any]] = {}
        self._locks: Dict[str, threading.RLock] = {}
        self._global_lock = threading.Lock()

    @property
    def _cache(self) -> Dict[str, Any]:
        """Backward compatibility alias for in-memory storage cache."""
        return self._storage

    def _get_repo_lock(self, repo_id: str) -> threading.RLock:
        with self._global_lock:
            if repo_id not in self._locks:
                self._locks[repo_id] = threading.RLock()
            return self._locks[repo_id]

    def _get_index_filepath(self, repo_id: str) -> Optional[str]:
        if not repo_id or not repo_id.strip():
            return None
        try:
            storage_root = RepositoryStorageService.get_repository_directory("")
            repo_dir = RepositoryStorageService.get_repository_directory(repo_id)
            if not RepositoryStorageService._is_safe_path(storage_root, repo_dir):
                return None
            index_path = os.path.join(repo_dir, self.INDEX_FILENAME)
            if not RepositoryStorageService._is_safe_path(repo_dir, index_path):
                return None
            return index_path
        except Exception:
            return None

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

    def _load_from_disk(self, repo_id: str) -> bool:
        if repo_id in self._storage and repo_id in self._metadata:
            return True

        index_path = self._get_index_filepath(repo_id)
        if not index_path or not os.path.exists(index_path) or not os.path.isfile(index_path):
            return False

        try:
            with open(index_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            if not isinstance(data, dict):
                return False

            metadata = data.get("metadata", {})
            raw_chunks = data.get("chunks", [])

            items: List[Tuple[CodeChunk, List[float]]] = []
            for item in raw_chunks:
                if isinstance(item, dict) and "chunk" in item and "embedding" in item:
                    try:
                        chunk = CodeChunk(**item["chunk"])
                        emb = [float(x) for x in item["embedding"]]
                        if chunk.repo_id == repo_id:
                            items.append((chunk, emb))
                    except Exception:
                        continue

            self._storage[repo_id] = items
            self._metadata[repo_id] = metadata
            return True
        except Exception as exc:
            logger.warning(f"Failed to parse persistent vector index for '{repo_id}': {str(exc)}")
            return False

    def _save_to_disk(self, repo_id: str) -> None:
        index_path = self._get_index_filepath(repo_id)
        if not index_path:
            return

        repo_dir = os.path.dirname(index_path)
        os.makedirs(repo_dir, exist_ok=True)

        items = self._storage.get(repo_id, [])
        metadata = self._metadata.get(repo_id, {})

        serialized_chunks = []
        for chunk, emb in items:
            if chunk.repo_id == repo_id:
                chunk_dict = chunk.dict() if hasattr(chunk, "dict") else chunk.model_dump()
                serialized_chunks.append({
                    "chunk": chunk_dict,
                    "embedding": emb,
                })

        data = {
            "metadata": metadata,
            "chunks": serialized_chunks,
        }

        tmp_path = index_path + ".tmp"
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

            os.replace(tmp_path, index_path)
        except Exception as exc:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass
            raise exc

    def has_repository(self, repo_id: str) -> bool:
        lock = self._get_repo_lock(repo_id)
        with lock:
            if repo_id in self._storage and len(self._storage[repo_id]) > 0:
                return True
            if self._load_from_disk(repo_id):
                return len(self._storage.get(repo_id, [])) > 0
            return False

    def get_repository_chunk_count(self, repo_id: str) -> int:
        lock = self._get_repo_lock(repo_id)
        with lock:
            if repo_id not in self._storage:
                self._load_from_disk(repo_id)
            return len(self._storage.get(repo_id, []))

    def set_repository_metadata(
        self, repo_id: str, provider: str, model: str, dimension: int
    ) -> None:
        lock = self._get_repo_lock(repo_id)
        with lock:
            if repo_id not in self._storage:
                self._load_from_disk(repo_id)

            self._metadata[repo_id] = {
                "provider": provider,
                "model": model,
                "dimension": dimension,
                "total_chunks": len(self._storage.get(repo_id, [])),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            self._save_to_disk(repo_id)

    def get_repository_metadata(self, repo_id: str) -> Optional[Dict[str, Any]]:
        lock = self._get_repo_lock(repo_id)
        with lock:
            if repo_id in self._metadata:
                return self._metadata.get(repo_id)
            if self._load_from_disk(repo_id):
                return self._metadata.get(repo_id)
            return None

    def add_chunks(
        self, repo_id: str, chunks: List[CodeChunk], embeddings: List[List[float]]
    ) -> None:
        lock = self._get_repo_lock(repo_id)
        with lock:
            if repo_id not in self._storage:
                self._load_from_disk(repo_id)
            if repo_id not in self._storage:
                self._storage[repo_id] = []

            for chunk, emb in zip(chunks, embeddings):
                if chunk.repo_id == repo_id:
                    self._storage[repo_id].append((chunk, emb))

            if repo_id in self._metadata:
                self._metadata[repo_id]["total_chunks"] = len(self._storage[repo_id])
            self._save_to_disk(repo_id)

    def delete_repository_vectors(self, repo_id: str) -> None:
        lock = self._get_repo_lock(repo_id)
        with lock:
            if repo_id in self._storage:
                del self._storage[repo_id]
            if repo_id in self._metadata:
                del self._metadata[repo_id]

            index_path = self._get_index_filepath(repo_id)
            if index_path:
                if os.path.exists(index_path):
                    try:
                        os.remove(index_path)
                    except Exception:
                        pass
                tmp_path = index_path + ".tmp"
                if os.path.exists(tmp_path):
                    try:
                        os.remove(tmp_path)
                    except Exception:
                        pass

    def search(
        self,
        repo_id: str,
        query_vector: List[float],
        top_k: int = 5,
        score_threshold: float = 0.0,
    ) -> List[Tuple[CodeChunk, float]]:
        lock = self._get_repo_lock(repo_id)
        with lock:
            if repo_id not in self._storage:
                self._load_from_disk(repo_id)

            repo_items = self._storage.get(repo_id, [])
            if not repo_items:
                return []

            scored_results: List[Tuple[CodeChunk, float]] = []
            for chunk, emb in repo_items:
                if chunk.repo_id != repo_id:
                    continue

                score = self._cosine_similarity(query_vector, emb)
                if score >= score_threshold:
                    scored_results.append((chunk, round(score, 4)))

            scored_results.sort(key=lambda x: (-x[1], x[0].chunk_id))
            return scored_results[:top_k]


# Global instance of vector store (PersistentVectorStore by default for AA.4)
global_vector_store = PersistentVectorStore()
