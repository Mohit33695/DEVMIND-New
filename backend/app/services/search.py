"""
Repository Code Search Service.

Purpose:
Provides safe, deterministic, server-side text search over stored repository source files.

Key Responsibilities:
1. Locate repository directory using RepositoryStorageService safely.
2. Recursively walk files while pruning IGNORED_DIRECTORIES and hidden files/folders.
3. Skip binary files (null byte check) and files > 2 MB.
4. Search lines for all occurrences of search query (case-sensitive or case-insensitive).
5. Return deterministic 1-indexed line results with character match offsets.
6. Enforce security checks preventing path traversal or code execution.
"""

import os
from typing import List, Optional

from app.schemas.search import RepositorySearchResponse, SearchResultItem
from app.services.scanner import IGNORED_DIRECTORIES
from app.services.storage import (
    RepositoryNotFoundError,
    RepositoryStorageService,
    ZipPathTraversalError,
)


class CodeSearchService:
    """Stateless service executing code text search over stored repositories."""

    # Maximum allowed character length for a returned line content snippet
    MAX_LINE_CONTENT_LENGTH = 500

    @classmethod
    def search_repository(
        cls,
        repo_id: str,
        query: str,
        case_sensitive: bool = False,
        max_results: int = 100,
        file_extension: Optional[str] = None,
    ) -> RepositorySearchResponse:
        """
        Executes raw source text search across stored repository files.

        Args:
            repo_id: Unique repository identifier.
            query: Search query string.
            case_sensitive: Whether match should be case-sensitive.
            max_results: Maximum number of matches to return (1-500).
            file_extension: Optional file extension filter (e.g. '.py', 'ts').

        Returns:
            RepositorySearchResponse: Structured response containing match details and search stats.

        Raises:
            RepositoryNotFoundError: If repository ID directory does not exist.
            ValueError: If query or parameters are invalid.
            ZipPathTraversalError: If security violation is detected.
        """
        # 1. Validate query
        if not query or not query.strip():
            raise ValueError("Search query cannot be empty or whitespace only.")

        # 2. Validate max_results boundary
        if max_results < 1 or max_results > 500:
            raise ValueError("max_results must be between 1 and 500.")

        # 3. Sanitize and validate file extension filter
        clean_ext: Optional[str] = None
        if file_extension and file_extension.strip():
            ext_str = file_extension.strip()
            if "/" in ext_str or "\\" in ext_str or ".." in ext_str:
                raise ZipPathTraversalError("Invalid file extension filter format.")
            clean_ext = ext_str.lower() if ext_str.startswith(".") else f".{ext_str.lower()}"

        # 4. Resolve repository directory
        if not repo_id or not repo_id.strip():
            raise RepositoryNotFoundError("Invalid or missing repository ID.")

        repo_dir = RepositoryStorageService.get_repository_directory(repo_id)
        if not os.path.exists(repo_dir) or not os.path.isdir(repo_dir):
            raise RepositoryNotFoundError(f"Repository with ID '{repo_id}' not found.")

        matches: List[SearchResultItem] = []
        total_files_searched = 0
        search_stop = False

        # 5. Walk repository tree safely
        for root, dirs, files in os.walk(repo_dir):
            if search_stop:
                break

            # Prune ignored and hidden directories in-place
            dirs[:] = [
                d for d in dirs
                if d not in IGNORED_DIRECTORIES and not d.startswith(".")
            ]

            # Sort dirs and files for deterministic traversal
            dirs.sort()
            files.sort()

            for file in files:
                if search_stop:
                    break

                # Skip hidden files
                if file.startswith("."):
                    continue

                # Filter by file extension if requested
                if clean_ext and not file.lower().endswith(clean_ext):
                    continue

                abs_file_path = os.path.join(root, file)

                # Security check: path traversal boundary
                if not RepositoryStorageService._is_safe_path(repo_dir, abs_file_path):
                    continue

                # Check file size (skip > 2 MB)
                try:
                    file_size = os.path.getsize(abs_file_path)
                except OSError:
                    continue

                if file_size > RepositoryStorageService.MAX_FILE_READ_SIZE_BYTES:
                    continue

                # Check binary null byte & read text content
                try:
                    with open(abs_file_path, "rb") as f:
                        raw_bytes = f.read()

                    if b"\x00" in raw_bytes[:1024]:
                        continue

                    text_content = raw_bytes.decode("utf-8")
                except (UnicodeDecodeError, OSError):
                    continue

                rel_file_path = os.path.relpath(abs_file_path, repo_dir).replace("\\", "/")
                total_files_searched += 1

                # Line-by-line matching
                lines = text_content.splitlines()
                for line_idx, line in enumerate(lines, start=1):
                    if search_stop:
                        break

                    target_line = line if case_sensitive else line.lower()
                    target_query = query if case_sensitive else query.lower()

                    query_len = len(target_query)
                    if query_len == 0:
                        continue

                    start_pos = 0
                    while True:
                        match_pos = target_line.find(target_query, start_pos)
                        if match_pos == -1:
                            break

                        match_start = match_pos
                        match_end = match_pos + query_len

                        # Truncate long lines to prevent bloated responses
                        line_snippet = line[: cls.MAX_LINE_CONTENT_LENGTH]

                        matches.append(
                            SearchResultItem(
                                file_path=rel_file_path,
                                line_number=line_idx,
                                line_content=line_snippet,
                                match_start=match_start,
                                match_end=match_end,
                            )
                        )

                        if len(matches) >= max_results:
                            search_stop = True
                            break

                        start_pos = match_pos + max(1, query_len)

        # 6. Sort results deterministically
        matches.sort(key=lambda m: (m.file_path, m.line_number, m.match_start))

        return RepositorySearchResponse(
            repo_id=repo_id,
            query=query,
            total_matches=len(matches),
            total_files_searched=total_files_searched,
            matches=matches,
        )
