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
import json
import logging
import os
import shutil
import uuid
import zipfile
from datetime import datetime, timezone
from typing import Any, BinaryIO, Dict, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)


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

    # Metadata file name stored inside each repository root
    META_FILENAME = ".devmind_meta.json"

    @classmethod
    def _validate_repo_id(cls, repo_id: str) -> str:
        """
        Validates that repo_id is a non-empty, safe string without path traversal attempts.
        """
        if not repo_id or not isinstance(repo_id, str) or not repo_id.strip():
            raise RepositoryNotFoundError("Invalid or missing repository ID.")
        cleaned_id = repo_id.strip()
        if (
            ".." in cleaned_id
            or "/" in cleaned_id
            or "\\" in cleaned_id
            or "\x00" in cleaned_id
        ):
            raise ZipPathTraversalError(
                f"Security risk detected: Repository ID '{repo_id}' contains invalid or malicious characters."
            )
        return cleaned_id

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

    @classmethod
    def save_repository_metadata(
        cls,
        repo_id: str,
        filename: str,
        size: int,
        scan_result: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        Saves repository metadata to .devmind_meta.json in the repository storage directory.
        """
        cleaned_id = cls._validate_repo_id(repo_id)
        repo_dir = cls.get_repository_directory(cleaned_id)
        if not os.path.exists(repo_dir) or not os.path.isdir(repo_dir):
            raise RepositoryNotFoundError(f"Repository with ID '{repo_id}' not found.")

        meta_path = os.path.join(repo_dir, cls.META_FILENAME)
        now_iso = datetime.now(timezone.utc).isoformat()

        scan_dict: Dict[str, Any] = {}
        if scan_result is not None:
            if hasattr(scan_result, "model_dump"):
                scan_dict = scan_result.model_dump()
            elif hasattr(scan_result, "dict"):
                scan_dict = scan_result.dict()
            elif isinstance(scan_result, dict):
                scan_dict = scan_result

        meta_data = {
            "repo_id": cleaned_id,
            "filename": filename or cleaned_id,
            "size": size,
            "uploaded_at": now_iso,
            "total_files": scan_dict.get("total_files", 0),
            "detected_languages": scan_dict.get("detected_languages", {}),
            "directories": scan_dict.get("directories", []),
            "scanned_files": scan_dict.get("scanned_files", []),
        }

        try:
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(meta_data, f, indent=2)
        except Exception as exc:
            logger.warning(f"Failed to write metadata for repository '{repo_id}': {exc}")

        return meta_data

    @classmethod
    def list_repositories(cls) -> List[Dict[str, Any]]:
        """
        Lists all stored repositories found in the managed storage directory.
        Handles missing or corrupted metadata safely by dynamically inspecting files.
        """
        if not os.path.exists(cls.BASE_STORAGE_DIR):
            return []

        repositories: List[Dict[str, Any]] = []

        try:
            entries = list(os.scandir(cls.BASE_STORAGE_DIR))
        except Exception as exc:
            logger.warning(f"Failed to scan repositories storage directory: {exc}")
            return []

        for entry in entries:
            if not entry.is_dir():
                continue

            repo_id = entry.name
            try:
                # Path traversal / validity check
                if ".." in repo_id or "/" in repo_id or "\\" in repo_id:
                    continue

                repo_dir = os.path.join(cls.BASE_STORAGE_DIR, repo_id)
                if not cls._is_safe_path(cls.BASE_STORAGE_DIR, repo_dir):
                    continue

                meta_path = os.path.join(repo_dir, cls.META_FILENAME)
                meta_data: Optional[Dict[str, Any]] = None

                if os.path.isfile(meta_path):
                    try:
                        with open(meta_path, "r", encoding="utf-8") as f:
                            loaded = json.load(f)
                        if isinstance(loaded, dict) and loaded.get("repo_id") == repo_id:
                            meta_data = loaded
                    except Exception:
                        meta_data = None

                # If metadata is missing or corrupted, scan on the fly
                if not meta_data:
                    from app.services.scanner import RepositoryScanner

                    scan_result = RepositoryScanner.scan_extracted_directory(repo_dir)
                    total_size = 0
                    for root, _, files in os.walk(repo_dir):
                        for fname in files:
                            fpath = os.path.join(root, fname)
                            try:
                                total_size += os.path.getsize(fpath)
                            except Exception:
                                pass

                    mtime = os.path.getmtime(repo_dir)
                    uploaded_at = datetime.fromtimestamp(mtime, tz=timezone.utc).isoformat()
                    meta_data = {
                        "repo_id": repo_id,
                        "filename": repo_id,
                        "size": total_size,
                        "uploaded_at": uploaded_at,
                        "total_files": scan_result.total_files,
                        "detected_languages": scan_result.detected_languages,
                        "directories": scan_result.directories,
                        "scanned_files": scan_result.scanned_files,
                    }
                    try:
                        with open(meta_path, "w", encoding="utf-8") as f:
                            json.dump(meta_data, f, indent=2)
                    except Exception:
                        pass

                indexing_status = "not_indexed"
                try:
                    from app.services.rag import CodebaseRAGService

                    rag_status = CodebaseRAGService.get_index_status(repo_id)
                    indexing_status = rag_status.status
                except Exception:
                    pass

                repositories.append(
                    {
                        "repo_id": repo_id,
                        "filename": meta_data.get("filename", repo_id),
                        "size": meta_data.get("size", 0),
                        "uploaded_at": meta_data.get("uploaded_at", ""),
                        "total_files": meta_data.get("total_files", 0),
                        "detected_languages": meta_data.get("detected_languages", {}),
                        "indexing_status": indexing_status,
                    }
                )
            except Exception as exc:
                logger.warning(f"Error reading repository '{repo_id}': {exc}")
                continue

        repositories.sort(key=lambda r: r.get("uploaded_at", ""), reverse=True)
        return repositories

    @classmethod
    def get_repository_detail(cls, repo_id: str) -> Dict[str, Any]:
        """
        Retrieves detailed metadata and reconstructed file tree for a stored repository.
        """
        cleaned_id = cls._validate_repo_id(repo_id)
        repo_dir = cls.get_repository_directory(cleaned_id)
        if not cls._is_safe_path(cls.BASE_STORAGE_DIR, repo_dir):
            raise ZipPathTraversalError("Security violation: Path traversal detected.")

        if not os.path.exists(repo_dir) or not os.path.isdir(repo_dir):
            raise RepositoryNotFoundError(f"Repository with ID '{repo_id}' not found.")

        meta_path = os.path.join(repo_dir, cls.META_FILENAME)
        meta_data: Optional[Dict[str, Any]] = None

        if os.path.isfile(meta_path):
            try:
                with open(meta_path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                if isinstance(loaded, dict) and loaded.get("repo_id") == cleaned_id:
                    meta_data = loaded
            except Exception:
                meta_data = None

        # Re-scan extracted directory to ensure accurate, up-to-date file tree
        from app.services.scanner import RepositoryScanner

        scan_result = RepositoryScanner.scan_extracted_directory(repo_dir)

        if not meta_data:
            total_size = 0
            for root, _, files in os.walk(repo_dir):
                for fname in files:
                    fpath = os.path.join(root, fname)
                    try:
                        total_size += os.path.getsize(fpath)
                    except Exception:
                        pass
            mtime = os.path.getmtime(repo_dir)
            uploaded_at = datetime.fromtimestamp(mtime, tz=timezone.utc).isoformat()
            meta_data = {
                "repo_id": cleaned_id,
                "filename": cleaned_id,
                "size": total_size,
                "uploaded_at": uploaded_at,
            }

        indexing_status = "not_indexed"
        try:
            from app.services.rag import CodebaseRAGService

            rag_status = CodebaseRAGService.get_index_status(cleaned_id)
            indexing_status = rag_status.status
        except Exception:
            pass

        return {
            "repo_id": cleaned_id,
            "filename": meta_data.get("filename", cleaned_id),
            "size": meta_data.get("size", 0),
            "uploaded_at": meta_data.get("uploaded_at", ""),
            "scan_result": scan_result,
            "indexing_status": indexing_status,
        }

    @classmethod
    def delete_repository(cls, repo_id: str) -> bool:
        """
        Safely deletes a stored repository, its source files, metadata, and vector index.
        Prevents deletion outside the managed storage directory.
        """
        cleaned_id = cls._validate_repo_id(repo_id)
        repo_dir = cls.get_repository_directory(cleaned_id)

        if (
            not cls._is_safe_path(cls.BASE_STORAGE_DIR, repo_dir)
            or os.path.abspath(repo_dir) == os.path.abspath(cls.BASE_STORAGE_DIR)
        ):
            raise ZipPathTraversalError(
                "Security risk detected: Attempted deletion outside managed storage."
            )

        if not os.path.exists(repo_dir) or not os.path.isdir(repo_dir):
            raise RepositoryNotFoundError(f"Repository with ID '{repo_id}' not found.")

        # 1. Clean up RAG vectors and status cache
        try:
            from app.services.rag import CodebaseRAGService

            CodebaseRAGService.delete_repository_index(cleaned_id)
        except Exception as exc:
            logger.warning(f"Error cleaning vector index for '{repo_id}': {exc}")

        # 2. Delete directory tree from disk
        shutil.rmtree(repo_dir)
        return True

