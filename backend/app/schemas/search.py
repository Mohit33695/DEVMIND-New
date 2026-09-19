"""
Pydantic schemas for repository code search models.
"""

from typing import List
from pydantic import BaseModel, Field


class SearchResultItem(BaseModel):
    """Individual search match item in a source file."""

    file_path: str = Field(..., description="Relative file path within repository")
    line_number: int = Field(..., description="1-indexed line number of match")
    line_content: str = Field(..., description="Text content of matching line (trimmed/truncated)")
    match_start: int = Field(..., description="0-indexed character start position of query match")
    match_end: int = Field(..., description="0-indexed character end position of query match")


class RepositorySearchResponse(BaseModel):
    """API response model for repository code search."""

    repo_id: str = Field(..., description="Repository unique identifier")
    query: str = Field(..., description="Original search query string")
    total_matches: int = Field(..., description="Total count of match occurrences returned")
    total_files_searched: int = Field(..., description="Total count of text files inspected")
    matches: List[SearchResultItem] = Field(
        default_factory=list, description="List of search match items"
    )
