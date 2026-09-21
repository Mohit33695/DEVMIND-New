"""
Codebase RAG Intelligence Service.

Purpose:
Orchestrates safe codebase file ingestion, hybrid symbol-aware chunking,
embedding generation, vector storage, and repository-scoped semantic retrieval with source citations.
"""

import os
import re
from typing import Dict, List, Optional, Set

from app.core.config import get_settings
from app.schemas.rag import (
    CodeChunk,
    RepositoryIndexStatus,
    RepositoryRetrievalResponse,
    RetrievalResult,
    SourceReference,
)
from app.schemas.symbols import SymbolItem
from app.services.chunking import HybridChunker
from app.services.embeddings import EmbeddingProvider, get_embedding_provider
from app.services.parser.service import CodeIntelligenceService
from app.services.scanner import RepositoryScanner
from app.services.storage import RepositoryNotFoundError, RepositoryStorageService
from app.services.vector_store import VectorStore, global_vector_store


def sanitize_error_message(text: str) -> str:
    """Sanitizes sensitive information (API keys, authorization headers) from exception messages."""
    if not text:
        return "Unknown error"
    # Redact Bearer tokens
    text = re.sub(r'Bearer\s+[A-Za-z0-9_\-\.]+', 'Bearer [REDACTED]', text)
    # Redact OpenAI style API keys (sk-...)
    text = re.sub(r'sk-[A-Za-z0-9_\-\.]+', '[REDACTED]', text)
    return text


class CodebaseRAGService:
    """Service handling repository vector indexing and semantic retrieval."""

    # In-memory index status tracking
    _status_cache: Dict[str, RepositoryIndexStatus] = {}

    @classmethod
    def get_embedding_provider(cls) -> EmbeddingProvider:
        """Returns the active embedding provider instance."""
        return get_embedding_provider()

    @classmethod
    def get_vector_store(cls) -> VectorStore:
        """Returns the active vector store instance."""
        return global_vector_store

    @classmethod
    def get_index_status(cls, repo_id: str) -> RepositoryIndexStatus:
        """
        Returns the indexing status of a repository.

        Args:
            repo_id: Unique repository identifier.

        Returns:
            RepositoryIndexStatus: Current status overview.
        """
        if not repo_id or not repo_id.strip():
            raise RepositoryNotFoundError("Invalid or missing repository ID.")

        repo_dir = RepositoryStorageService.get_repository_directory(repo_id)
        if not os.path.exists(repo_dir) or not os.path.isdir(repo_dir):
            raise RepositoryNotFoundError(f"Repository with ID '{repo_id}' not found.")

        vector_store = cls.get_vector_store()
        provider = cls.get_embedding_provider()

        if repo_id in cls._status_cache:
            status_obj = cls._status_cache[repo_id]
            if status_obj.status in ("indexing", "failed"):
                return status_obj
            if vector_store.has_repository(repo_id):
                status_obj.total_chunks = vector_store.get_repository_chunk_count(repo_id)
                return status_obj

        if vector_store.has_repository(repo_id):
            chunk_cnt = vector_store.get_repository_chunk_count(repo_id)
            return RepositoryIndexStatus(
                repo_id=repo_id,
                status="indexed",
                total_files=0,
                indexed_files=0,
                total_chunks=chunk_cnt,
                embedding_dimension=provider.get_dimension(),
                embedding_provider=provider.get_provider_name(),
            )

        return RepositoryIndexStatus(
            repo_id=repo_id,
            status="not_indexed",
            total_files=0,
            indexed_files=0,
            total_chunks=0,
            embedding_dimension=provider.get_dimension(),
            embedding_provider=provider.get_provider_name(),
        )

    @classmethod
    def index_repository(cls, repo_id: str) -> RepositoryIndexStatus:
        """
        Indexes stored repository source code into vector storage.

        Args:
            repo_id: Unique repository identifier.

        Returns:
            RepositoryIndexStatus: Aggregated indexing status metrics.

        Raises:
            RepositoryNotFoundError: If repository ID does not exist in storage.
        """
        if not repo_id or not repo_id.strip():
            raise RepositoryNotFoundError("Invalid or missing repository ID.")

        repo_dir = RepositoryStorageService.get_repository_directory(repo_id)
        if not os.path.exists(repo_dir) or not os.path.isdir(repo_dir):
            raise RepositoryNotFoundError(f"Repository with ID '{repo_id}' not found.")

        provider = cls.get_embedding_provider()
        vector_store = cls.get_vector_store()
        settings = get_settings()

        # Mark status as indexing
        cls._status_cache[repo_id] = RepositoryIndexStatus(
            repo_id=repo_id,
            status="indexing",
            total_files=0,
            indexed_files=0,
            total_chunks=0,
            embedding_dimension=provider.get_dimension(),
            embedding_provider=provider.get_provider_name(),
        )

        try:
            # 1. Enumerate repository files
            scan_result = RepositoryScanner.scan_extracted_directory(repo_dir)
            all_files = scan_result.scanned_files
            total_scanned = len(all_files)

            # Filter allowlist
            indexable_files = [f for f in all_files if HybridChunker.is_indexable_file(f)]

            # 2. Extract symbols
            extracted_symbols_resp = CodeIntelligenceService.extract_repository_symbols(repo_id)
            symbols_by_file: Dict[str, List[SymbolItem]] = {}
            for fs in extracted_symbols_resp.file_symbols:
                symbols_by_file[fs.file_path] = fs.symbols

            all_chunks: List[CodeChunk] = []

            # 3. Read and Chunk Indexable Files
            indexed_files_count = 0
            for rel_path in indexable_files:
                abs_path = os.path.join(repo_dir, rel_path)

                try:
                    if os.path.getsize(abs_path) > RepositoryStorageService.MAX_FILE_READ_SIZE_BYTES:
                        continue
                    with open(abs_path, "rb") as f:
                        raw_bytes = f.read()
                    if b"\x00" in raw_bytes[:1024]:
                        continue
                    file_text = raw_bytes.decode("utf-8", errors="ignore")
                except Exception:
                    continue

                file_symbols = symbols_by_file.get(rel_path, [])
                file_chunks = HybridChunker.chunk_file_lines(repo_id, rel_path, file_text, file_symbols)

                if file_chunks:
                    all_chunks.extend(file_chunks)
                    indexed_files_count += 1

            # 4. Generate Vector Embeddings
            chunk_contents = [c.content for c in all_chunks]
            embeddings: List[List[float]] = []

            if chunk_contents:
                embeddings = provider.embed_texts(chunk_contents)

            # 5. Clear old index & Save new vectors + metadata to vector store
            vector_store.delete_repository_vectors(repo_id)

            if all_chunks and embeddings:
                vector_store.add_chunks(repo_id, all_chunks, embeddings)
                vector_store.set_repository_metadata(
                    repo_id=repo_id,
                    provider=provider.get_provider_name(),
                    model=settings.EMBEDDING_MODEL,
                    dimension=provider.get_dimension(),
                )

            status_obj = RepositoryIndexStatus(
                repo_id=repo_id,
                status="indexed",
                total_files=total_scanned,
                indexed_files=indexed_files_count,
                total_chunks=len(all_chunks),
                embedding_dimension=provider.get_dimension(),
                embedding_provider=provider.get_provider_name(),
            )
            cls._status_cache[repo_id] = status_obj
            return status_obj

        except Exception as exc:
            # Clean up partial vectors completely on failure
            vector_store.delete_repository_vectors(repo_id)
            sanitized_err = sanitize_error_message(str(exc))
            status_obj = RepositoryIndexStatus(
                repo_id=repo_id,
                status="failed",
                total_files=0,
                indexed_files=0,
                total_chunks=0,
                embedding_dimension=provider.get_dimension(),
                embedding_provider=provider.get_provider_name(),
                error=f"Indexing failed: {sanitized_err}",
            )
            cls._status_cache[repo_id] = status_obj
            return status_obj

    @classmethod
    def retrieve_codebase_context(
        cls,
        repo_id: str,
        query: str,
        top_k: int = 5,
        score_threshold: float = 0.0,
    ) -> RepositoryRetrievalResponse:
        """
        Executes semantic RAG vector retrieval scoped strictly to repo_id.

        Args:
            repo_id: Unique repository identifier.
            query: Natural language search query string.
            top_k: Maximum number of results to return (1 to 20).
            score_threshold: Minimum similarity threshold.

        Returns:
            RepositoryRetrievalResponse: Retrieved chunk results with source references.
        """
        if not repo_id or not repo_id.strip():
            raise RepositoryNotFoundError("Invalid or missing repository ID.")

        repo_dir = RepositoryStorageService.get_repository_directory(repo_id)
        if not os.path.exists(repo_dir) or not os.path.isdir(repo_dir):
            raise RepositoryNotFoundError(f"Repository with ID '{repo_id}' not found.")

        if not query or not query.strip():
            raise ValueError("Query string cannot be empty.")

        # Constrain top_k boundary (1 <= top_k <= 20)
        bounded_top_k = max(1, min(top_k, 20))

        provider = cls.get_embedding_provider()
        vector_store = cls.get_vector_store()
        settings = get_settings()

        # If repo is not indexed yet, auto-index it
        if not vector_store.has_repository(repo_id):
            cls.index_repository(repo_id)
        else:
            # Check metadata for mismatch without auto-reindexing
            indexed_meta = vector_store.get_repository_metadata(repo_id)
            if indexed_meta:
                curr_provider = provider.get_provider_name()
                curr_model = settings.EMBEDDING_MODEL
                curr_dim = provider.get_dimension()

                if (
                    indexed_meta.get("provider") != curr_provider
                    or indexed_meta.get("model") != curr_model
                    or indexed_meta.get("dimension") != curr_dim
                ):
                    raise ValueError(
                        f"Repository '{repo_id}' index requires re-indexing due to an embedding provider, "
                        f"model, or dimension change. Please explicitly call POST /api/repositories/{repo_id}/index."
                    )

        # 1. Embed query
        query_vectors = provider.embed_texts([query])
        if not query_vectors:
            return RepositoryRetrievalResponse(repo_id=repo_id, query=query, results=[])

        query_vec = query_vectors[0]

        # 2. Search strictly within repository partition
        search_hits = vector_store.search(
            repo_id=repo_id,
            query_vector=query_vec,
            top_k=bounded_top_k,
            score_threshold=score_threshold,
        )

        results: List[RetrievalResult] = []
        seen_chunks: Set[str] = set()

        for chunk, score in search_hits:
            if chunk.chunk_id in seen_chunks:
                continue
            seen_chunks.add(chunk.chunk_id)

            source_ref = SourceReference(
                file_path=chunk.file_path,
                start_line=chunk.start_line,
                end_line=chunk.end_line,
                symbol_name=chunk.symbol_name,
                relevance_score=score,
            )

            results.append(
                RetrievalResult(
                    chunk=chunk,
                    relevance_score=score,
                    source_reference=source_ref,
                )
            )

        return RepositoryRetrievalResponse(
            repo_id=repo_id,
            query=query,
            results=results,
        )
