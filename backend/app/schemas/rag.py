"""
RAG / Codebase Intelligence Schemas.

Purpose:
Defines Pydantic data schemas for repository indexing, code chunks,
vector retrieval results, source references, and embedding status.
"""

from typing import List, Optional
from pydantic import BaseModel


class CodeChunk(BaseModel):
    """Metadata and text content of a single codebase chunk."""

    chunk_id: str
    repo_id: str
    file_path: str
    language: str
    start_line: int
    end_line: int
    symbol_name: Optional[str] = None
    symbol_kind: Optional[str] = None
    content: str
    content_hash: str


class SourceReference(BaseModel):
    """Source code citation details for UI navigation and LLM context."""

    file_path: str
    start_line: int
    end_line: int
    symbol_name: Optional[str] = None
    relevance_score: float


class RetrievalResult(BaseModel):
    """Individual retrieved code chunk result with similarity score."""

    chunk: CodeChunk
    relevance_score: float
    source_reference: SourceReference


class RepositoryRetrievalRequest(BaseModel):
    """Request payload for semantic codebase vector retrieval."""

    query: str
    top_k: int = 5
    score_threshold: Optional[float] = 0.0


class RepositoryRetrievalResponse(BaseModel):
    """Complete response payload for semantic codebase retrieval."""

    repo_id: str
    query: str
    results: List[RetrievalResult] = []


class RepositoryIndexStatus(BaseModel):
    """Indexing status overview for a stored repository."""

    repo_id: str
    status: str  # not_indexed, indexing, indexed, failed
    total_files: int = 0
    indexed_files: int = 0
    total_chunks: int = 0
    embedding_dimension: int = 384
    embedding_provider: str = "MockEmbeddingProvider (Development/Test Mode)"
    error: Optional[str] = None
