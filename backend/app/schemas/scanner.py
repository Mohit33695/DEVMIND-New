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

