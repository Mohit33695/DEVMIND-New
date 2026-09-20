"""
Git Intelligence Service.

Purpose:
Statically inspects Git repository metadata, commit logs, author contributions,
file modification frequency, and activity timelines without executing repository code,
scripts, hooks, or external build commands.
"""

from datetime import datetime, timezone
import os
from typing import Dict, List, Optional, Set, Tuple

import git

from app.schemas.git import (
    GitActivityPoint,
    GitCommitItem,
    GitContributorItem,
    GitFileHistoryItem,
    GitRepositorySummary,
    RepositoryGitResponse,
)
from app.services.storage import RepositoryNotFoundError, RepositoryStorageService

# Enforce strict read-only security configuration for Git environment
os.environ["GIT_CONFIG_NOSYSTEM"] = "1"
os.environ["GIT_CONFIG_GLOBAL"] = os.devnull
os.environ["GIT_OPT_OUT_OF_UNSAFE_EXTENSIONS"] = "1"


class CodeGitService:
    """Service for safe static Git metadata analysis."""

    @classmethod
    def analyze_repository_git(
        cls, repo_id: str, max_commits: int = 200
    ) -> RepositoryGitResponse:
        """
        Statically reads Git metadata, commit history, contributor activity, and file hotspots.

        Args:
            repo_id: Unique repository identifier.
            max_commits: Maximum number of commits to analyze (1 to 500).

        Returns:
            RepositoryGitResponse: Aggregated Git intelligence response.

        Raises:
            RepositoryNotFoundError: If repository ID does not exist in storage.
        """
        if not repo_id or not repo_id.strip():
            raise RepositoryNotFoundError("Invalid or missing repository ID.")

        repo_dir = RepositoryStorageService.get_repository_directory(repo_id)
        if not os.path.exists(repo_dir) or not os.path.isdir(repo_dir):
            raise RepositoryNotFoundError(f"Repository with ID '{repo_id}' not found.")

        # Constrain max_commits boundary (1 <= max_commits <= 500)
        bounded_max_commits = max(1, min(max_commits, 500))

        git_dir = os.path.join(repo_dir, ".git")

        # 1. No .git metadata present
        if not os.path.exists(git_dir) or not os.path.isdir(git_dir):
            return RepositoryGitResponse(
                repo_id=repo_id,
                summary=GitRepositorySummary(
                    has_git_metadata=False,
                    current_branch="none",
                    head_commit_hash=None,
                    analyzed_commit_count=0,
                    total_contributors=0,
                    oldest_commit_date=None,
                    newest_commit_date=None,
                ),
                commits=[],
                contributors=[],
                top_changed_files=[],
                activity_timeline=[],
            )

        # 2. Inspect Git repository safely via GitPython
        try:
            repo = git.Repo(repo_dir)
        except Exception:
            # Corrupt or unreadable .git directory
            return RepositoryGitResponse(
                repo_id=repo_id,
                summary=GitRepositorySummary(
                    has_git_metadata=False,
                    current_branch="corrupt",
                    head_commit_hash=None,
                    analyzed_commit_count=0,
                    total_contributors=0,
                    oldest_commit_date=None,
                    newest_commit_date=None,
                ),
                commits=[],
                contributors=[],
                top_changed_files=[],
                activity_timeline=[],
            )

        # Determine current branch safely
        current_branch = "HEAD"
        try:
            current_branch = repo.active_branch.name
        except Exception:
            try:
                current_branch = f"HEAD ({repo.head.commit.hexsha[:7]})"
            except Exception:
                current_branch = "HEAD"

        commits_list: List[GitCommitItem] = []
        contributors_map: Dict[Tuple[str, str], Dict] = {}
        file_hotspots_map: Dict[str, Dict] = {}
        activity_map: Dict[str, int] = {}

        # 3. Read commits up to bounded_max_commits
        try:
            git_commits = list(repo.iter_commits(max_count=bounded_max_commits))
        except Exception:
            git_commits = []

        if not git_commits:
            return RepositoryGitResponse(
                repo_id=repo_id,
                summary=GitRepositorySummary(
                    has_git_metadata=True,
                    current_branch=current_branch,
                    head_commit_hash=None,
                    analyzed_commit_count=0,
                    total_contributors=0,
                    oldest_commit_date=None,
                    newest_commit_date=None,
                ),
                commits=[],
                contributors=[],
                top_changed_files=[],
                activity_timeline=[],
            )

        head_commit_hash = git_commits[0].hexsha

        for commit in git_commits:
            full_hash = commit.hexsha
            short_hash = full_hash[:7]

            author_name = str(commit.author.name or "Unknown").strip()[:100]
            author_email = str(commit.author.email or "").strip()[:100]

            dt = datetime.fromtimestamp(commit.committed_date, tz=timezone.utc)
            iso_timestamp = dt.isoformat()
            date_key = dt.strftime("%Y-%m-%d")

            raw_msg = (commit.message or "").strip().splitlines()
            clean_message = raw_msg[0][:250] if raw_msg else ""

            # Stat metrics safely
            files_changed_count = 0
            insertions = 0
            deletions = 0
            changed_files: List[str] = []

            try:
                stats = commit.stats
                files_changed_count = len(stats.files)
                insertions = stats.total.get("insertions", 0)
                deletions = stats.total.get("deletions", 0)
                changed_files = list(stats.files.keys())
            except Exception:
                pass

            commits_list.append(
                GitCommitItem(
                    hash=full_hash,
                    short_hash=short_hash,
                    author_name=author_name,
                    author_email=author_email,
                    timestamp=iso_timestamp,
                    message=clean_message,
                    files_changed_count=files_changed_count,
                    insertions=insertions,
                    deletions=deletions,
                )
            )

            # Aggregate Contributor Activity
            contrib_key = (author_email.lower(), author_name.lower())
            if contrib_key not in contributors_map:
                contributors_map[contrib_key] = {
                    "name": author_name,
                    "email": author_email,
                    "commit_count": 0,
                    "first_commit_date": iso_timestamp,
                    "last_commit_date": iso_timestamp,
                }

            contrib = contributors_map[contrib_key]
            contrib["commit_count"] += 1
            # Update dates (since commits are iterated newest -> oldest)
            contrib["first_commit_date"] = iso_timestamp  # Keeps overwriting to older
            # last_commit_date remains the newest timestamp encountered first

            # Aggregate Daily Activity Timeline
            activity_map[date_key] = activity_map.get(date_key, 0) + 1

            # Aggregate File Activity Hotspots
            for raw_fpath in changed_files:
                fpath = raw_fpath.replace("\\", "/").strip()
                if not fpath or fpath.startswith(".git"):
                    continue

                abs_target = os.path.join(repo_dir, fpath)
                if not RepositoryStorageService._is_safe_path(repo_dir, abs_target):
                    continue

                if fpath not in file_hotspots_map:
                    file_hotspots_map[fpath] = {
                        "file_path": fpath,
                        "commit_count": 0,
                        "last_commit_hash": short_hash,
                        "last_commit_date": iso_timestamp,
                        "last_author": author_name,
                    }

                fh = file_hotspots_map[fpath]
                fh["commit_count"] += 1

        # 4. Format & Sort Collections Deterministically
        # Contributors: Sort by commit_count desc, name asc, email asc
        contributors_list = [
            GitContributorItem(
                name=c["name"],
                email=c["email"],
                commit_count=c["commit_count"],
                first_commit_date=c["first_commit_date"],
                last_commit_date=c["last_commit_date"],
            )
            for c in contributors_map.values()
        ]
        contributors_list.sort(
            key=lambda x: (-x.commit_count, x.name.lower(), x.email.lower())
        )

        # File Hotspots: Sort by commit_count desc, file_path asc; Top 50
        hotspots_list = [
            GitFileHistoryItem(
                file_path=h["file_path"],
                commit_count=h["commit_count"],
                last_commit_hash=h["last_commit_hash"],
                last_commit_date=h["last_commit_date"],
                last_author=h["last_author"],
            )
            for h in file_hotspots_map.values()
        ]
        hotspots_list.sort(key=lambda x: (-x.commit_count, x.file_path.lower()))
        top_hotspots = hotspots_list[:50]

        # Activity Timeline: Sort by date asc (YYYY-MM-DD)
        timeline_list = [
            GitActivityPoint(date=d, commit_count=cnt)
            for d, cnt in activity_map.items()
        ]
        timeline_list.sort(key=lambda x: x.date)

        newest_date = commits_list[0].timestamp if commits_list else None
        oldest_date = commits_list[-1].timestamp if commits_list else None

        summary = GitRepositorySummary(
            has_git_metadata=True,
            current_branch=current_branch,
            head_commit_hash=head_commit_hash,
            analyzed_commit_count=len(commits_list),
            total_contributors=len(contributors_list),
            oldest_commit_date=oldest_date,
            newest_commit_date=newest_date,
        )

        return RepositoryGitResponse(
            repo_id=repo_id,
            summary=summary,
            commits=commits_list,
            contributors=contributors_list,
            top_changed_files=top_hotspots,
            activity_timeline=timeline_list,
        )
