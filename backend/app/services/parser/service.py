"""
Code Intelligence Service.

Purpose:
Orchestrates static code symbol extraction across stored repository files.
Uses ParserRegistry to dispatch parsing to the appropriate parser implementation:
- Python (.py) uses native Python AST (PythonParser).
- JS/JSX/TS/TSX use Tree-sitter (TypeScriptTreeSitterParser).
"""

import os
from typing import List, Set

from app.schemas.symbols import FileSymbols, RepositorySymbolsResponse
from app.services.parser.registry import ParserRegistry
from app.services.scanner import RepositoryScanner
from app.services.storage import RepositoryNotFoundError, RepositoryStorageService


class CodeIntelligenceService:
    """Service for extracting code intelligence symbols from stored repositories."""

    # 2 MB maximum file size cap for AST parsing
    MAX_FILE_PARSE_SIZE_BYTES = 2 * 1024 * 1024

    # Ignored directory set
    IGNORED_DIRS: Set[str] = {
        "node_modules",
        "dist",
        "build",
        ".git",
        "venv",
        ".venv",
    }

    @classmethod
    def extract_repository_symbols(cls, repo_id: str) -> RepositorySymbolsResponse:
        """
        Extracts code symbols from supported source files in a stored repository.

        Args:
            repo_id: Unique repository identifier.

        Returns:
            RepositorySymbolsResponse: Grouped symbol lists per file and total count.

        Raises:
            RepositoryNotFoundError: If repository ID directory does not exist.
        """
        if not repo_id or not repo_id.strip():
            raise RepositoryNotFoundError("Invalid or missing repository ID.")

        repo_dir = RepositoryStorageService.get_repository_directory(repo_id)
        if not os.path.exists(repo_dir) or not os.path.isdir(repo_dir):
            raise RepositoryNotFoundError(f"Repository with ID '{repo_id}' not found.")

        registry = ParserRegistry()
        file_symbols_list: List[FileSymbols] = []
        total_symbols = 0

        for root, dirs, files in os.walk(repo_dir):
            # Prune ignored directory names in-place
            dirs[:] = [
                d for d in dirs if d not in cls.IGNORED_DIRS and not d.startswith(".")
            ]

            rel_root = os.path.relpath(root, repo_dir)

            for file in files:
                if file.startswith(".git"):
                    continue

                abs_file_path = os.path.join(root, file)
                rel_file_path = (
                    file if rel_root == "." else os.path.join(rel_root, file)
                ).replace("\\", "/")

                # Enforce 2 MB size cap
                if os.path.getsize(abs_file_path) > cls.MAX_FILE_PARSE_SIZE_BYTES:
                    continue

                parser = registry.get_parser_for_file(rel_file_path)
                if parser is None:
                    continue

                symbols = parser.parse_file(abs_file_path, rel_file_path)
                if symbols:
                    language = RepositoryScanner.detect_language(rel_file_path)
                    file_symbols_list.append(
                        FileSymbols(
                            file_path=rel_file_path,
                            language=language,
                            symbols=symbols,
                        )
                    )
                    total_symbols += len(symbols)

        # Sort file symbols by file path
        file_symbols_list.sort(key=lambda x: x.file_path)

        return RepositorySymbolsResponse(
            repo_id=repo_id,
            total_symbols=total_symbols,
            file_symbols=file_symbols_list,
        )

