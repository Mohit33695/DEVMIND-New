"""
Unit tests for RepositoryStorageService.
"""

import io
import os
import shutil
import zipfile
import pytest

from app.services.storage import (
    BinaryFileError,
    FileTooLargeError,
    RepositoryFileNotFoundError,
    RepositoryNotFoundError,
    RepositoryStorageService,
    ZipPathTraversalError,
)


def create_sample_zip(files_map: dict) -> bytes:
    """Helper utility to create a zip file buffer from a filename -> content dict."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for filename, content in files_map.items():
            if isinstance(content, bytes):
                zf.writestr(filename, content)
            else:
                zf.writestr(filename, content)
    return buffer.getvalue()


def test_store_repository_zip_creates_unique_repo_id():
    """Verifies that store_repository_zip generates a unique repo_id and persistent directory."""
    files = {"src/App.py": "print('hello world')", "README.md": "# Readme"}
    zip_bytes = create_sample_zip(files)

    repo_id, dest_dir = RepositoryStorageService.store_repository_zip(zip_bytes)

    try:
        # 1. Assert unique repo_id string generated
        assert isinstance(repo_id, str)
        assert len(repo_id) > 0

        # 2. Assert destination directory exists on disk
        assert os.path.exists(dest_dir)
        assert os.path.isabs(dest_dir)

        # 3. Assert files remain available after function call completes
        app_file_path = os.path.join(dest_dir, "src", "App.py")
        readme_file_path = os.path.join(dest_dir, "README.md")

        assert os.path.isfile(app_file_path)
        assert os.path.isfile(readme_file_path)

        with open(app_file_path, "r", encoding="utf-8") as f:
            assert f.read() == "print('hello world')"
    finally:
        # Cleanup test files from storage
        if os.path.exists(dest_dir):
            shutil.rmtree(dest_dir, ignore_errors=True)


def test_store_repository_zip_path_traversal_protection():
    """Verifies that store_repository_zip rejects Zip Slip path traversal attempts."""
    malicious_files = {
        "normal.txt": "normal file",
        "../evil.txt": "hacked file",
    }
    zip_bytes = create_sample_zip(malicious_files)

    with pytest.raises(ZipPathTraversalError) as exc_info:
        RepositoryStorageService.store_repository_zip(zip_bytes)

    assert "path traversal" in str(exc_info.value).lower()


def test_read_repository_file_content_success():
    """Verifies reading text file content from a stored repository."""
    files = {"src/main.py": "def main(): return 42\n"}
    zip_bytes = create_sample_zip(files)
    repo_id, dest_dir = RepositoryStorageService.store_repository_zip(zip_bytes)

    try:
        response = RepositoryStorageService.read_repository_file_content(repo_id, "src/main.py")
        assert response.repo_id == repo_id
        assert response.path == "src/main.py"
        assert response.content == "def main(): return 42\n"
        assert response.size == len("def main(): return 42\n")
    finally:
        if os.path.exists(dest_dir):
            shutil.rmtree(dest_dir, ignore_errors=True)


def test_read_repository_file_content_repo_not_found():
    """Verifies that requesting a non-existent repo_id raises RepositoryNotFoundError."""
    with pytest.raises(RepositoryNotFoundError):
        RepositoryStorageService.read_repository_file_content("non-existent-repo-id-12345", "main.py")


def test_read_repository_file_content_file_not_found():
    """Verifies that requesting a non-existent file path inside a repo raises RepositoryFileNotFoundError."""
    files = {"README.md": "# Title"}
    zip_bytes = create_sample_zip(files)
    repo_id, dest_dir = RepositoryStorageService.store_repository_zip(zip_bytes)

    try:
        with pytest.raises(RepositoryFileNotFoundError):
            RepositoryStorageService.read_repository_file_content(repo_id, "does_not_exist.py")
    finally:
        if os.path.exists(dest_dir):
            shutil.rmtree(dest_dir, ignore_errors=True)


def test_read_repository_file_content_path_traversal():
    """Verifies that requesting a path traversal file raises ZipPathTraversalError."""
    files = {"README.md": "# Title"}
    zip_bytes = create_sample_zip(files)
    repo_id, dest_dir = RepositoryStorageService.store_repository_zip(zip_bytes)

    try:
        with pytest.raises(ZipPathTraversalError):
            RepositoryStorageService.read_repository_file_content(repo_id, "../../../etc/passwd")
    finally:
        if os.path.exists(dest_dir):
            shutil.rmtree(dest_dir, ignore_errors=True)


def test_read_repository_file_content_binary():
    """Verifies that reading a binary file raises BinaryFileError."""
    binary_content = b"\x00\x01\x02\x03\xff\xfe"
    files = {"image.png": binary_content}
    zip_bytes = create_sample_zip(files)
    repo_id, dest_dir = RepositoryStorageService.store_repository_zip(zip_bytes)

    try:
        with pytest.raises(BinaryFileError):
            RepositoryStorageService.read_repository_file_content(repo_id, "image.png")
    finally:
        if os.path.exists(dest_dir):
            shutil.rmtree(dest_dir, ignore_errors=True)

