"""
Git Intelligence Schemas.

Purpose:
Defines Pydantic data schemas for static Git history metadata, commit logs,
contributor statistics, file activity hotspots, and commit activity timelines.
"""

from typing import List, Optional
from pydantic import BaseModel


class GitCommitItem(BaseModel):
    """Details of a single Git commit."""

    hash: str
    short_hash: str
    author_name: str
    author_email: str
    timestamp: str
    message: str
    files_changed_count: int
    insertions: int
    deletions: int


class GitContributorItem(BaseModel):
    """Aggregated author/contributor activity statistics."""

    name: str
    email: str
    commit_count: int
    first_commit_date: str
    last_commit_date: str


class GitFileHistoryItem(BaseModel):
    """File modification frequency and recent change metadata (hotspot)."""

    file_path: str
    commit_count: int
    last_commit_hash: str
    last_commit_date: str
    last_author: str


class GitActivityPoint(BaseModel):
    """Daily commit frequency data point for activity timeline visualization."""

    date: str  # YYYY-MM-DD
    commit_count: int


class GitRepositorySummary(BaseModel):
    """High-level summary of repository Git metadata."""

    has_git_metadata: bool
    current_branch: str
    head_commit_hash: Optional[str] = None
    analyzed_commit_count: int
    total_contributors: int
    oldest_commit_date: Optional[str] = None
    newest_commit_date: Optional[str] = None


class RepositoryGitResponse(BaseModel):
    """Complete Git Intelligence API response."""

    repo_id: str
    summary: GitRepositorySummary
    commits: List[GitCommitItem] = []
    contributors: List[GitContributorItem] = []
    top_changed_files: List[GitFileHistoryItem] = []
    activity_timeline: List[GitActivityPoint] = []
