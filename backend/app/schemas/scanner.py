"""
Pydantic schemas for repository scanning models.
"""

from typing import Dict, List
from pydantic import BaseModel, Field


class RepositoryScanResult(BaseModel):
    """Scan metadata output produced by RepositoryScanner."""

    total_files: int = Field(
        ..., description="Total count of non-ignored files discovered in repository"
    )
    detected_languages: Dict[str, int] = Field(
        default_factory=dict,
        description="Mapping of detected programming language names to file counts",
    )
    directories: List[str] = Field(
        default_factory=list,
        description="Sorted list of relative directory paths discovered",
    )
    scanned_files: List[str] = Field(
        default_factory=list,
        description="Sorted list of relative file paths discovered",
    )


class RepositoryFileContentResponse(BaseModel):
    """File content response model for repository file retrieval."""

    repo_id: str = Field(..., description="Repository unique identifier")
    path: str = Field(..., description="Relative file path within repository")
    size: int = Field(..., description="File size in bytes")
    content: str = Field(..., description="File text content")
    encoding: str = Field(default="utf-8", description="Character encoding format")


class RepositorySummary(BaseModel):
    """Summary item representing a stored repository."""

    repo_id: str = Field(..., description="Repository unique identifier")
    filename: str = Field(..., description="Repository or archive filename")
    size: int = Field(..., description="Repository size in bytes")
    uploaded_at: str = Field(..., description="ISO 8601 upload timestamp")
    total_files: int = Field(..., description="Total count of discovered source files")
    detected_languages: Dict[str, int] = Field(
        default_factory=dict,
        description="Distribution of detected programming languages",
    )
    indexing_status: str = Field(
        default="not_indexed",
        description="RAG vector indexing status (not_indexed, indexing, indexed, failed)",
    )


class RepositoryDetailResponse(BaseModel):
    """Detailed repository response containing scan result and file tree."""

    repo_id: str = Field(..., description="Repository unique identifier")
    filename: str = Field(..., description="Repository name or archive filename")
    size: int = Field(..., description="Repository size in bytes")
    uploaded_at: str = Field(..., description="ISO 8601 upload timestamp")
    scan_result: RepositoryScanResult = Field(..., description="Full repository scan result")
    indexing_status: str = Field(
        default="not_indexed",
        description="RAG vector indexing status (not_indexed, indexing, indexed, failed)",
    )


class RepositoryDeleteResponse(BaseModel):
    """Response confirming repository deletion."""

    repo_id: str = Field(..., description="Repository unique identifier")
    deleted: bool = Field(default=True, description="Deletion confirmation flag")
    message: str = Field(..., description="Status message")

