"""
Hybrid Chunker Service.

Purpose:
Performs symbol-aware code chunking using polyglot symbol line ranges,
with line-overlapping fallback for plain text, configuration, and documentation files.
"""

import hashlib
import os
from typing import Dict, List, Optional, Set, Tuple

from app.schemas.rag import CodeChunk
from app.schemas.symbols import SymbolItem
from app.services.scanner import RepositoryScanner


class HybridChunker:
    """Service generating deterministic symbol-aware and line-bounded code chunks."""

    # File Extension Allowlist
    SUPPORTED_EXTENSIONS: Set[str] = {
        # Source Code
        ".py",
        ".ts",
        ".tsx",
        ".js",
        ".jsx",
        ".java",
        ".go",
        ".c",
        ".cpp",
        ".h",
        ".hpp",
        ".cs",
        ".rs",
        ".rb",
        ".php",
        ".sh",
        # Data & Config
        ".json",
        ".yaml",
        ".yml",
        ".toml",
        ".sql",
        ".html",
        ".css",
        ".xml",
        # Documentation
        ".md",
        ".markdown",
        ".rst",
        ".txt",
    }

    # Line-based chunking defaults for non-symbol content
    DEFAULT_CHUNK_LINES = 30
    DEFAULT_OVERLAP_LINES = 5
    MAX_CHUNK_CHARS = 4000

    IGNORED_PATH_PARTS: Set[str] = {
        "node_modules",
        ".git",
        "dist",
        "build",
        "venv",
        ".venv",
        "__pycache__",
        ".pytest_cache",
    }

    @classmethod
    def is_indexable_file(cls, rel_path: str) -> bool:
        """Determines whether a file path conforms to the indexing allowlist."""
        rel_lower = rel_path.lower().replace("\\", "/")
        base_name = os.path.basename(rel_lower)
        _, ext = os.path.splitext(rel_lower)

        # Exclude ignored directory paths
        path_parts = set(rel_lower.split("/"))
        if path_parts.intersection(cls.IGNORED_PATH_PARTS):
            return False

        # Exclude minified files
        if base_name.endswith(".min.js") or base_name.endswith(".min.css") or base_name.endswith(".bundle.js"):
            return False

        return ext in cls.SUPPORTED_EXTENSIONS

    @classmethod
    def _create_chunk_object(
        cls,
        repo_id: str,
        file_path: str,
        language: str,
        start_line: int,
        end_line: int,
        content: str,
        symbol_name: Optional[str] = None,
        symbol_kind: Optional[str] = None,
    ) -> CodeChunk:
        """Helper creating a CodeChunk model with deterministic SHA-256 content hashing."""
        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        chunk_raw_id = f"{repo_id}:{file_path}:{start_line}:{end_line}:{content_hash[:8]}"
        chunk_id = hashlib.sha256(chunk_raw_id.encode("utf-8")).hexdigest()[:16]

        return CodeChunk(
            chunk_id=chunk_id,
            repo_id=repo_id,
            file_path=file_path,
            language=language,
            start_line=start_line,
            end_line=end_line,
            symbol_name=symbol_name,
            symbol_kind=symbol_kind,
            content=content,
            content_hash=content_hash,
        )

    @classmethod
    def chunk_file_lines(
        cls,
        repo_id: str,
        file_path: str,
        file_text: str,
        symbols: Optional[List[SymbolItem]] = None,
    ) -> List[CodeChunk]:
        """
        Chunks a file text using symbol-aware boundaries when symbols are available,
        falling back to line-overlapping chunks for un-symbolized regions or non-symbol files.
        """
        chunks: List[CodeChunk] = []
        lines = file_text.splitlines()

        if not lines:
            return chunks

        language = RepositoryScanner.detect_language(file_path)
        total_lines = len(lines)

        covered_lines: Set[int] = set()

        # 1. Symbol-Aware Chunking
        if symbols:
            for sym in symbols:
                if sym.line_start <= total_lines:
                    start_l = max(1, sym.line_start)
                    end_l = min(total_lines, sym.line_end)

                    if start_l > end_l:
                        continue

                    sym_lines = lines[start_l - 1 : end_l]
                    sym_content = "\n".join(sym_lines)

                    if not sym_content.strip():
                        continue

                    # If symbol content exceeds MAX_CHUNK_CHARS, sub-split it by lines
                    if len(sym_content) > cls.MAX_CHUNK_CHARS:
                        sub_chunks = cls._chunk_by_lines_range(
                            repo_id, file_path, language, lines, start_l, end_l, sym.name, sym.kind
                        )
                        chunks.extend(sub_chunks)
                    else:
                        chunk_obj = cls._create_chunk_object(
                            repo_id=repo_id,
                            file_path=file_path,
                            language=language,
                            start_line=start_l,
                            end_line=end_l,
                            content=sym_content,
                            symbol_name=sym.name,
                            symbol_kind=sym.kind,
                        )
                        chunks.append(chunk_obj)

                    for line_idx in range(start_l, end_l + 1):
                        covered_lines.add(line_idx)

        # 2. Fill Uncovered Line Regions with Line-Overlapping Chunks
        uncovered_start: Optional[int] = None

        for line_num in range(1, total_lines + 1):
            if line_num not in covered_lines:
                if uncovered_start is None:
                    uncovered_start = line_num
            else:
                if uncovered_start is not None:
                    sub_chunks = cls._chunk_by_lines_range(
                        repo_id, file_path, language, lines, uncovered_start, line_num - 1
                    )
                    chunks.extend(sub_chunks)
                    uncovered_start = None

        if uncovered_start is not None:
            sub_chunks = cls._chunk_by_lines_range(
                repo_id, file_path, language, lines, uncovered_start, total_lines
            )
            chunks.extend(sub_chunks)

        # Sort chunks deterministically by start_line
        chunks.sort(key=lambda c: (c.start_line, c.end_line, c.chunk_id))
        return chunks

    @classmethod
    def _chunk_by_lines_range(
        cls,
        repo_id: str,
        file_path: str,
        language: str,
        all_lines: List[str],
        range_start: int,
        range_end: int,
        symbol_name: Optional[str] = None,
        symbol_kind: Optional[str] = None,
    ) -> List[CodeChunk]:
        """Helper to create line-overlapping chunks for a line range."""
        range_chunks: List[CodeChunk] = []

        curr_start = range_start
        step = cls.DEFAULT_CHUNK_LINES - cls.DEFAULT_OVERLAP_LINES
        if step <= 0:
            step = 25

        while curr_start <= range_end:
            curr_end = min(range_end, curr_start + cls.DEFAULT_CHUNK_LINES - 1)
            chunk_lines = all_lines[curr_start - 1 : curr_end]
            chunk_content = "\n".join(chunk_lines)

            if chunk_content.strip():
                range_chunks.append(
                    cls._create_chunk_object(
                        repo_id=repo_id,
                        file_path=file_path,
                        language=language,
                        start_line=curr_start,
                        end_line=curr_end,
                        content=chunk_content,
                        symbol_name=symbol_name,
                        symbol_kind=symbol_kind,
                    )
                )

            if curr_end >= range_end:
                break
            curr_start += step

        return range_chunks
