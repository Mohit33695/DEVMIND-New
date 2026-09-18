"""
Repository Scanner Service.

Purpose:
Provides safe, isolated inspection and scanning of uploaded repository ZIP archives.

Key Responsibilities:
1. Safely extract ZIP archives to temporary directories.
2. Protect against Zip Slip / path traversal security vulnerabilities.
3. Traverse repository files without executing any code or scripts.
4. Filter out ignored build/dependency directories (node_modules, dist, .git, etc.).
5. Detect programming languages based on file extensions.
6. Return structured repository metadata.
"""

import io
import os
import tempfile
import zipfile
from typing import BinaryIO, Dict, List, Set, Union

from app.schemas.scanner import RepositoryScanResult

# Directories to ignore during scanning
IGNORED_DIRECTORIES: Set[str] = {
    "node_modules",
    "dist",
    "build",
    ".git",
    "venv",
    ".venv",
}

# Mapping of file extensions to programming languages
EXTENSION_LANGUAGE_MAP: Dict[str, str] = {
    # Python
    ".py": "Python",
    ".pyw": "Python",
    # JavaScript & TypeScript
    ".js": "JavaScript",
    ".mjs": "JavaScript",
    ".cjs": "JavaScript",
    ".jsx": "JavaScript React",
    ".ts": "TypeScript",
    ".mts": "TypeScript",
    ".cts": "TypeScript",
    ".tsx": "TypeScript React",
    # Web & Styles
    ".html": "HTML",
    ".htm": "HTML",
    ".css": "CSS",
    ".scss": "CSS",
    ".sass": "CSS",
    ".less": "CSS",
    # Systems & Compiled
    ".c": "C",
    ".h": "C",
    ".cpp": "C++",
    ".cc": "C++",
    ".cxx": "C++",
    ".hpp": "C++",
    ".cs": "C#",
    ".java": "Java",
    ".go": "Go",
    ".rs": "Rust",
    ".swift": "Swift",
    ".kt": "Kotlin",
    ".kts": "Kotlin",
    # Scripting
    ".rb": "Ruby",
    ".php": "PHP",
    ".sh": "Shell",
    ".bash": "Shell",
    ".zsh": "Shell",
    ".bat": "Shell",
    ".ps1": "Shell",
    # Data & Config
    ".json": "JSON",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".toml": "TOML",
    ".xml": "XML",
    ".sql": "SQL",
    ".md": "Markdown",
    ".markdown": "Markdown",
}


class ZipPathTraversalError(ValueError):
    """Exception raised when a zip entry attempts path traversal (Zip Slip)."""

    pass


class RepositoryScanner:
    """Dedicated scanner service for inspecting repository archives safely."""

    @staticmethod
    def _is_safe_path(base_dir: str, target_path: str) -> bool:
        """
        Validates that target_path resides safely within base_dir.
        Prevents Zip Slip (Path Traversal) vulnerabilities.
        """
        abs_base = os.path.abspath(base_dir)
        abs_target = os.path.abspath(target_path)
        return os.path.commonpath([abs_base, abs_target]) == abs_base

    @classmethod
    def detect_language(cls, filename: str) -> str:
        """Determines the programming language of a file based on extension."""
        basename = os.path.basename(filename)
        if basename == "Dockerfile":
            return "Docker"

        _, ext = os.path.splitext(filename.lower())
        return EXTENSION_LANGUAGE_MAP.get(ext, "Other")

    @classmethod
    def scan_extracted_directory(cls, target_dir: str) -> RepositoryScanResult:
        """
        Recursively inspects an already extracted repository directory on disk.

        Args:
            target_dir: Path to extracted repository directory.

        Returns:
            RepositoryScanResult: Extracted metadata including file counts, languages, and structure.
        """
        total_files = 0
        detected_languages: Dict[str, int] = {}
        directories: Set[str] = set()
        scanned_files: List[str] = []

        for root, dirs, files in os.walk(target_dir):
            # Filter ignored directory names in-place so os.walk skips them
            dirs[:] = [
                d for d in dirs if d not in IGNORED_DIRECTORIES and not d.startswith(".")
            ]

            rel_root = os.path.relpath(root, target_dir)
            if rel_root != ".":
                # Normalize path separators for consistent output
                norm_dir = rel_root.replace("\\", "/")
                directories.add(norm_dir)

            for file in files:
                # Skip hidden system/git files if any
                if file.startswith(".git"):
                    continue

                rel_filepath = (
                    file
                    if rel_root == "."
                    else os.path.join(rel_root, file)
                ).replace("\\", "/")

                # Detect programming language
                lang = cls.detect_language(file)
                detected_languages[lang] = detected_languages.get(lang, 0) + 1

                total_files += 1
                scanned_files.append(rel_filepath)

        return RepositoryScanResult(
            total_files=total_files,
            detected_languages=detected_languages,
            directories=sorted(list(directories)),
            scanned_files=sorted(scanned_files),
        )

    @classmethod
    def scan_zip_file(
        cls, file_source: Union[BinaryIO, bytes, str]
    ) -> RepositoryScanResult:
        """
        Safely inspects and scans a repository ZIP archive.

        Args:
            file_source: Binary file object, bytes, or file path to ZIP archive.

        Returns:
            RepositoryScanResult: Extracted metadata including file counts, languages, and structure.

        Raises:
            ZipPathTraversalError: If zip contains invalid/malicious path traversal entries.
            zipfile.BadZipFile: If zip header is invalid.
        """
        if isinstance(file_source, bytes):
            zip_input = io.BytesIO(file_source)
        else:
            zip_input = file_source

        with tempfile.TemporaryDirectory() as temp_dir:
            with zipfile.ZipFile(zip_input, "r") as zf:
                # 1. Validate all entries for Zip Slip before extracting
                for member in zf.infolist():
                    target_path = os.path.join(temp_dir, member.filename)
                    if not cls._is_safe_path(temp_dir, target_path):
                        raise ZipPathTraversalError(
                            f"Security risk detected: ZIP entry '{member.filename}' "
                            "attempts path traversal outside destination directory."
                        )

                # 2. Extract contents into temp directory safely
                zf.extractall(temp_dir)

            # 3. Scan extracted temp directory
            return cls.scan_extracted_directory(temp_dir)

