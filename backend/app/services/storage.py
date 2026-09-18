"""
Repository Storage Service.

Purpose:
Manages persistent storage for uploaded repository archives on disk.

Key Responsibilities:
1. Generate unique UUID repository identifiers (repo_id).
2. Create dedicated storage directories under backend/storage/repositories/{repo_id}/.
3. Inspect and extract uploaded ZIP archives safely into managed storage.
4. Protect against Zip Slip (path traversal) vulnerabilities.
5. Provide helper methods to locate stored repositories.
"""

import io
import os
import uuid
import zipfile
from typing import BinaryIO, Optional, Tuple, Union


from app.schemas.scanner import RepositoryFileContentResponse


class ZipPathTraversalError(ValueError):
    """Exception raised when a zip entry or path request attempts path traversal (Zip Slip)."""

    pass


class RepositoryNotFoundError(ValueError):
    """Exception raised when a requested repository ID does not exist in storage."""

    pass


class RepositoryFileNotFoundError(ValueError):
    """Exception raised when a requested relative file path does not exist within a repository."""

    pass


class FileTooLargeError(ValueError):
    """Exception raised when a requested file exceeds the maximum readable size limit."""

    pass


class BinaryFileError(ValueError):
    """Exception raised when a requested file contains binary/non-text data."""

    pass


class RepositoryStorageService:
    """Service handling persistent extraction, storage, and retrieval of repository files."""

    # Maximum file content read size limit (2 MB)
    MAX_FILE_READ_SIZE_BYTES = 2 * 1024 * 1024

    # Default storage root path: backend/storage/repositories
    BASE_STORAGE_DIR = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "storage", "repositories")
    )

    @classmethod
    def _is_safe_path(cls, base_dir: str, target_path: str) -> bool:
        """
        Validates that target_path resides safely within base_dir.
        Prevents Zip Slip (Path Traversal) security vulnerabilities.
        """
        abs_base = os.path.abspath(base_dir)
        abs_target = os.path.abspath(target_path)
        return os.path.commonpath([abs_base, abs_target]) == abs_base

    @classmethod
    def get_repository_directory(cls, repo_id: str) -> str:
        """Returns absolute filesystem path for a stored repository ID."""
        repo_dir = os.path.join(cls.BASE_STORAGE_DIR, repo_id)
        return os.path.abspath(repo_dir)

    @classmethod
    def store_repository_zip(
        cls,
        file_source: Union[BinaryIO, bytes, str],
        repo_id: Optional[str] = None,
    ) -> Tuple[str, str]:
        """
        Safely extracts and stores a repository ZIP archive into backend managed storage.

        Args:
            file_source: Binary file object, bytes, or file path to ZIP archive.
            repo_id: Optional custom repository UUID (auto-generated if None).

        Returns:
            Tuple[str, str]: (repo_id, destination_directory_path)

        Raises:
            ZipPathTraversalError: If zip archive contains Zip Slip path traversal entries.
            zipfile.BadZipFile: If zip header is invalid.
        """
        if not repo_id:
            repo_id = str(uuid.uuid4())

        destination_dir = cls.get_repository_directory(repo_id)
        os.makedirs(destination_dir, exist_ok=True)

        if isinstance(file_source, bytes):
            zip_input = io.BytesIO(file_source)
        else:
            zip_input = file_source

        with zipfile.ZipFile(zip_input, "r") as zf:
            # 1. Inspect and validate all entries for Zip Slip before extraction
            for member in zf.infolist():
                target_path = os.path.join(destination_dir, member.filename)
                if not cls._is_safe_path(destination_dir, target_path):
                    raise ZipPathTraversalError(
                        f"Security risk detected: ZIP entry '{member.filename}' "
                        "attempts path traversal outside destination directory."
                    )

            # 2. Extract contents safely into the managed storage directory
            zf.extractall(destination_dir)

        return repo_id, destination_dir

    @classmethod
    def read_repository_file_content(
        cls, repo_id: str, relative_path: str
    ) -> RepositoryFileContentResponse:
        """
        Safely reads the text content of a file within a stored repository.

        Args:
            repo_id: Unique repository identifier.
            relative_path: Relative file path within the repository directory.

        Returns:
            RepositoryFileContentResponse: Structured file metadata and text content.

        Raises:
            RepositoryNotFoundError: If repository ID directory does not exist.
            ZipPathTraversalError: If relative_path attempts path traversal outside repository root.
            RepositoryFileNotFoundError: If requested file path does not exist or is a directory.
            FileTooLargeError: If file size exceeds 2 MB limit.
            BinaryFileError: If file contains binary / non-text content.
        """
        if not repo_id or not repo_id.strip():
            raise RepositoryNotFoundError("Invalid or missing repository ID.")

        repo_dir = cls.get_repository_directory(repo_id)
        if not os.path.exists(repo_dir) or not os.path.isdir(repo_dir):
            raise RepositoryNotFoundError(f"Repository with ID '{repo_id}' not found.")

        normalized_rel_path = relative_path.replace("\\", "/").strip()
        if not normalized_rel_path:
            raise RepositoryFileNotFoundError("File path cannot be empty.")

        target_file_path = os.path.join(repo_dir, normalized_rel_path)

        # 1. Path traversal security check
        if not cls._is_safe_path(repo_dir, target_file_path):
            raise ZipPathTraversalError(
                f"Security risk detected: File path '{relative_path}' "
                "attempts path traversal outside repository directory."
            )

        # 2. File existence check
        if not os.path.exists(target_file_path) or not os.path.isfile(target_file_path):
            raise RepositoryFileNotFoundError(
                f"File '{normalized_rel_path}' not found in repository '{repo_id}'."
            )

        # 3. Maximum file size check (2 MB)
        file_size = os.path.getsize(target_file_path)
        if file_size > cls.MAX_FILE_READ_SIZE_BYTES:
            raise FileTooLargeError(
                f"File '{normalized_rel_path}' size ({file_size} bytes) "
                f"exceeds maximum allowed limit of {cls.MAX_FILE_READ_SIZE_BYTES // (1024 * 1024)} MB."
            )

        # 4. Binary check & UTF-8 decoding
        try:
            with open(target_file_path, "rb") as f:
                raw_bytes = f.read()

            # Check for null bytes indicative of binary files
            if b"\x00" in raw_bytes[:1024]:
                raise BinaryFileError(
                    f"File '{normalized_rel_path}' is binary and cannot be displayed as text."
                )

            text_content = raw_bytes.decode("utf-8")
        except UnicodeDecodeError:
            raise BinaryFileError(
                f"File '{normalized_rel_path}' contains non-text or binary encoding."
            )

        return RepositoryFileContentResponse(
            repo_id=repo_id,
            path=normalized_rel_path,
            size=file_size,
            content=text_content,
            encoding="utf-8",
        )

