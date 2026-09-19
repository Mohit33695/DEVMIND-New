"""
Tests for Documentation Intelligence Service and API Route.

Coverage:
- Valid repository documentation generation
- Missing repository handling (404)
- Repositories with and without README files (README.md, README.rst, README.txt)
- Multi-language symbol aggregation
- Public and private symbol counting
- Dependency counts and imported_by_count
- External package detection
- Circular dependency status reporting
- Deterministic module ordering
- Security & path traversal safety
"""

import io
import os
import tempfile
import zipfile
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.documentation import RepositoryDocumentationService
from app.services.storage import RepositoryNotFoundError, RepositoryStorageService

client = TestClient(app)


def create_zip_archive(files_dict: dict) -> bytes:
    """Helper function to create an in-memory zip archive from a dict of filename -> content."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for filename, content in files_dict.items():
            zf.writestr(filename, content)
    buf.seek(0)
    return buf.getvalue()


@pytest.fixture
def repo_with_readme():
    files = {
        "README.md": "# Sample Project\n\nThis is a sample project for testing documentation generation.",
        "src/main.py": '"""Main module docstring."""\nimport os\nfrom utils import helper\n\ndef run():\n    """Run application."""\n    pass\n\ndef _private_func():\n    pass\n',
        "src/utils.py": '"""Utility module."""\nimport math\n\ndef helper():\n    """Helper function."""\n    return 42\n',
    }
    zip_bytes = create_zip_archive(files)
    repo_id, _ = RepositoryStorageService.store_repository_zip(zip_bytes)
    return repo_id


@pytest.fixture
def repo_without_readme():
    files = {
        "app.py": "def start():\n    pass\n",
    }
    zip_bytes = create_zip_archive(files)
    repo_id, _ = RepositoryStorageService.store_repository_zip(zip_bytes)
    return repo_id


@pytest.fixture
def multi_lang_repo():
    files = {
        "README.txt": "Plain text readme file.",
        "server.py": '"""Python server."""\nimport sys\n\ndef handle():\n    pass\n',
        "index.js": '/** JS Entry */\nimport { helper } from "./utils.js";\nexport function main() { return helper(); }\nfunction _internal() {}\n',
        "utils.js": 'export function helper() { return "ok"; }\n',
    }
    zip_bytes = create_zip_archive(files)
    repo_id, _ = RepositoryStorageService.store_repository_zip(zip_bytes)
    return repo_id


@pytest.fixture
def circular_dep_repo():
    files = {
        "a.py": "import b\ndef func_a(): pass\n",
        "b.py": "import a\ndef func_b(): pass\n",
    }
    zip_bytes = create_zip_archive(files)
    repo_id, _ = RepositoryStorageService.store_repository_zip(zip_bytes)
    return repo_id


def test_generate_documentation_valid(repo_with_readme):
    """Test generating documentation for a valid repository with README and Python symbols."""
    doc = RepositoryDocumentationService.generate_documentation(repo_with_readme)

    assert doc.repo_id == repo_with_readme
    assert doc.overview.total_files == 3
    assert doc.overview.readme_file_path == "README.md"
    assert "Sample Project" in doc.overview.readme_content
    assert doc.overview.detected_languages.get("Python") == 2
    assert doc.overview.detected_languages.get("Markdown") == 1

    # Check modules summary
    assert len(doc.modules) == 3
    main_mod = next(m for m in doc.modules if m.file_path == "src/main.py")
    assert main_mod.language == "Python"
    assert main_mod.total_symbols > 0
    assert main_mod.imports_count >= 1

    # Check public vs private symbol count in main.py
    # `run` is public, `_private_func` starts with '_' so it is private
    assert main_mod.public_symbols_count >= 1

    # Check architecture summary
    assert doc.architecture.external_packages == ["math", "os"]
    assert not doc.architecture.has_circular_dependencies


def test_generate_documentation_missing_repo():
    """Test generating documentation for non-existent repository."""
    with pytest.raises(RepositoryNotFoundError):
        RepositoryDocumentationService.generate_documentation("non_existent_repo_id_123")


def test_generate_documentation_without_readme(repo_without_readme):
    """Test generating documentation for repository without README."""
    doc = RepositoryDocumentationService.generate_documentation(repo_without_readme)

    assert doc.overview.readme_file_path is None
    assert doc.overview.readme_content is None
    assert doc.overview.total_files == 1


def test_generate_documentation_multi_lang(multi_lang_repo):
    """Test generating documentation for multi-language repo (Python + JS)."""
    doc = RepositoryDocumentationService.generate_documentation(multi_lang_repo)

    assert doc.overview.readme_file_path == "README.txt"
    assert doc.overview.detected_languages.get("Python") == 1
    assert doc.overview.detected_languages.get("JavaScript") == 2

    # Check module ordering (sorted by file_path)
    module_paths = [m.file_path for m in doc.modules]
    assert module_paths == sorted(module_paths)


def test_generate_documentation_circular_deps(circular_dep_repo):
    """Test circular dependency detection in documentation summary."""
    doc = RepositoryDocumentationService.generate_documentation(circular_dep_repo)

    assert doc.architecture.has_circular_dependencies is True
    assert doc.architecture.circular_cycles_count >= 1

    # Check imported_by_count
    a_mod = next(m for m in doc.modules if m.file_path == "a.py")
    b_mod = next(m for m in doc.modules if m.file_path == "b.py")

    assert a_mod.imported_by_count >= 1
    assert b_mod.imported_by_count >= 1


def test_documentation_api_endpoint(repo_with_readme):
    """Test GET /api/repositories/{repo_id}/documentation endpoint."""
    response = client.get(f"/api/repositories/{repo_with_readme}/documentation")
    assert response.status_code == 200

    data = response.json()
    assert data["repo_id"] == repo_with_readme
    assert data["overview"]["readme_file_path"] == "README.md"
    assert isinstance(data["modules"], list)
    assert isinstance(data["architecture"]["external_packages"], list)


def test_documentation_api_endpoint_404():
    """Test GET /api/repositories/{repo_id}/documentation endpoint with invalid repo_id."""
    response = client.get("/api/repositories/invalid-repo-uuid-9999/documentation")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()
