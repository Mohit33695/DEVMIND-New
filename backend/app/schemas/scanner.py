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
