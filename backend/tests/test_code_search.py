"""
Unit and API integration tests for Repository Code Search.
"""

import io
import os
import shutil
import zipfile
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.search import CodeSearchService
from app.services.storage import RepositoryNotFoundError, RepositoryStorageService

client = TestClient(app)


def create_sample_zip(files_map: dict) -> bytes:
    """Helper utility to create a zip file buffer from a filename -> content dict."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for filename, content in files_map.items():
            if isinstance(content, bytes):
                zf.writestr(filename, content)
            else:
                zf.writestr(filename, str(content))
    return buffer.getvalue()


@pytest.fixture
def sample_repo():
    """Fixture that creates a temporary test repository and cleans up afterwards."""
    files = {
        "src/main.py": "def hello_world():\n    print('Hello World')\n    return 'hello'\n",
        "src/utils.py": "def calculate():\n    # hello helper\n    return 42\n",
        "docs/README.md": "# Sample Repo\nThis project says hello world to everyone.\n",
    }
    zip_bytes = create_sample_zip(files)
    repo_id, dest_dir = RepositoryStorageService.store_repository_zip(zip_bytes)
    yield repo_id, dest_dir
    if os.path.exists(dest_dir):
        shutil.rmtree(dest_dir, ignore_errors=True)


def test_single_file_query_match(sample_repo):
    """1. Single-file query match."""
    repo_id, _ = sample_repo
    response = CodeSearchService.search_repository(repo_id, query="calculate")

    assert response.repo_id == repo_id
    assert response.query == "calculate"
    assert response.total_matches == 1
    assert len(response.matches) == 1
    assert response.matches[0].file_path == "src/utils.py"
    assert response.matches[0].line_number == 1
    assert "def calculate():" in response.matches[0].line_content


def test_multiple_occurrences_one_line():
    """2. Multiple occurrences on one line."""
    files = {
        "src/dup.py": "def hello_world(hello_param):\n    return 'hello'\n"
    }
    zip_bytes = create_sample_zip(files)
    repo_id, dest_dir = RepositoryStorageService.store_repository_zip(zip_bytes)

    try:
        res = CodeSearchService.search_repository(repo_id, query="hello")
        line1_matches = [m for m in res.matches if m.line_number == 1]
        assert len(line1_matches) == 2
        assert line1_matches[0].match_start == 4
        assert line1_matches[1].match_start == 16
    finally:
        if os.path.exists(dest_dir):
            shutil.rmtree(dest_dir, ignore_errors=True)


def test_multiple_files_search(sample_repo):
    """3. Multiple files search."""
    repo_id, _ = sample_repo
    res = CodeSearchService.search_repository(repo_id, query="hello")

    matched_files = {m.file_path for m in res.matches}
    assert "src/main.py" in matched_files
    assert "src/utils.py" in matched_files
    assert "docs/README.md" in matched_files


def test_case_insensitive_search(sample_repo):
    """4. Case-insensitive search."""
    repo_id, _ = sample_repo
    res = CodeSearchService.search_repository(repo_id, query="HELLO", case_sensitive=False)
    assert res.total_matches > 0
    # Should match 'Hello World', 'hello', etc.
    matched_texts = [m.line_content for m in res.matches]
    assert any("Hello World" in t for t in matched_texts)


def test_case_sensitive_search(sample_repo):
    """5. Case-sensitive search."""
    repo_id, _ = sample_repo
    res_sensitive = CodeSearchService.search_repository(repo_id, query="Hello", case_sensitive=True)
    matched_lines = [m.line_content for m in res_sensitive.matches]

    assert any("print('Hello World')" in line for line in matched_lines)
    # Should NOT match lowercase 'def hello_world' when case_sensitive=True
    assert not any("def hello_world()" in line for line in matched_lines)


def test_max_results_limit():
    """6. max_results limit."""
    files = {
        "lines.txt": "\n".join([f"match_target line {i}" for i in range(20)])
    }
    zip_bytes = create_sample_zip(files)
    repo_id, dest_dir = RepositoryStorageService.store_repository_zip(zip_bytes)

    try:
        res = CodeSearchService.search_repository(repo_id, query="match_target", max_results=5)
        assert res.total_matches == 5
        assert len(res.matches) == 5
    finally:
        if os.path.exists(dest_dir):
            shutil.rmtree(dest_dir, ignore_errors=True)


def test_file_extension_filter(sample_repo):
    """7. file_extension filter."""
    repo_id, _ = sample_repo
    res = CodeSearchService.search_repository(repo_id, query="hello", file_extension=".py")
    matched_files = {m.file_path for m in res.matches}

    assert "src/main.py" in matched_files
    assert "src/utils.py" in matched_files
    assert "docs/README.md" not in matched_files


def test_ignored_directories():
    """8. ignored directories: node_modules, dist, build, .git, venv, .venv."""
    files = {
        "src/app.js": "const target = 1;\n",
        "node_modules/package/index.js": "const target = 2;\n",
        "dist/bundle.js": "const target = 3;\n",
        "build/main.js": "const target = 4;\n",
        ".git/config": "target = 5\n",
        "venv/lib/site.py": "target = 6\n",
        ".venv/lib/site.py": "target = 7\n",
    }
    zip_bytes = create_sample_zip(files)
    repo_id, dest_dir = RepositoryStorageService.store_repository_zip(zip_bytes)

    try:
        res = CodeSearchService.search_repository(repo_id, query="target")
        matched_files = [m.file_path for m in res.matches]

        assert matched_files == ["src/app.js"]
    finally:
        if os.path.exists(dest_dir):
            shutil.rmtree(dest_dir, ignore_errors=True)


def test_hidden_directories():
    """9. hidden directories."""
    files = {
        "src/app.py": "find_me = True\n",
        ".secret_dir/hidden.py": "find_me = True\n",
    }
    zip_bytes = create_sample_zip(files)
    repo_id, dest_dir = RepositoryStorageService.store_repository_zip(zip_bytes)

    try:
        res = CodeSearchService.search_repository(repo_id, query="find_me")
        matched_files = [m.file_path for m in res.matches]
        assert matched_files == ["src/app.py"]
    finally:
        if os.path.exists(dest_dir):
            shutil.rmtree(dest_dir, ignore_errors=True)


def test_hidden_files():
    """10. hidden files."""
    files = {
        "src/app.py": "secret_key = 123\n",
        ".env": "secret_key = 456\n",
    }
    zip_bytes = create_sample_zip(files)
    repo_id, dest_dir = RepositoryStorageService.store_repository_zip(zip_bytes)

    try:
        res = CodeSearchService.search_repository(repo_id, query="secret_key")
        matched_files = [m.file_path for m in res.matches]
        assert matched_files == ["src/app.py"]
    finally:
        if os.path.exists(dest_dir):
            shutil.rmtree(dest_dir, ignore_errors=True)


def test_binary_file_skipping():
    """11. binary file skipping."""
    binary_content = b"\x00\x01\x02binary search_term\x00data"
    files = {
        "src/app.py": "search_term = True\n",
        "assets/image.bin": binary_content,
    }
    zip_bytes = create_sample_zip(files)
    repo_id, dest_dir = RepositoryStorageService.store_repository_zip(zip_bytes)

    try:
        res = CodeSearchService.search_repository(repo_id, query="search_term")
        matched_files = [m.file_path for m in res.matches]
        assert matched_files == ["src/app.py"]
    finally:
        if os.path.exists(dest_dir):
            shutil.rmtree(dest_dir, ignore_errors=True)


def test_files_larger_than_2mb():
    """12. files larger than 2 MB."""
    # Create content slightly over 2 MB
    large_text = "search_target\n" + ("x" * (2 * 1024 * 1024 + 100))
    files = {
        "src/small.py": "search_target = 1\n",
        "src/large.txt": large_text,
    }
    zip_bytes = create_sample_zip(files)
    repo_id, dest_dir = RepositoryStorageService.store_repository_zip(zip_bytes)

    try:
        res = CodeSearchService.search_repository(repo_id, query="search_target")
        matched_files = [m.file_path for m in res.matches]
        assert matched_files == ["src/small.py"]
    finally:
        if os.path.exists(dest_dir):
            shutil.rmtree(dest_dir, ignore_errors=True)


def test_non_utf8_file_handling():
    """13. non-UTF-8 file handling."""
    invalid_utf8_content = b"hello \x80\xff world search_target"
    files = {
        "src/good.py": "search_target = 1\n",
        "src/bad_encoding.txt": invalid_utf8_content,
    }
    zip_bytes = create_sample_zip(files)
    repo_id, dest_dir = RepositoryStorageService.store_repository_zip(zip_bytes)

    try:
        res = CodeSearchService.search_repository(repo_id, query="search_target")
        matched_files = [m.file_path for m in res.matches]
        assert matched_files == ["src/good.py"]
    finally:
        if os.path.exists(dest_dir):
            shutil.rmtree(dest_dir, ignore_errors=True)


def test_nonexistent_repository_404():
    """14. nonexistent repository -> 404."""
    response = client.get("/api/repositories/nonexistent-repo-99999/search?q=test")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_empty_query_400(sample_repo):
    """15. empty query -> 400."""
    repo_id, _ = sample_repo
    response = client.get(f"/api/repositories/{repo_id}/search?q=")
    assert response.status_code == 422 or response.status_code == 400


def test_whitespace_only_query_400(sample_repo):
    """16. whitespace-only query -> 400."""
    repo_id, _ = sample_repo
    response = client.get(f"/api/repositories/{repo_id}/search?q=   ")
    assert response.status_code == 400
    assert "empty or whitespace" in response.json()["detail"].lower()


def test_deterministic_result_ordering():
    """17. deterministic result ordering."""
    files = {
        "z_file.py": "item\n",
        "a_file.py": "item\nitem\n",
    }
    zip_bytes = create_sample_zip(files)
    repo_id, dest_dir = RepositoryStorageService.store_repository_zip(zip_bytes)

    try:
        res = CodeSearchService.search_repository(repo_id, query="item")
        paths = [(m.file_path, m.line_number, m.match_start) for m in res.matches]

        assert paths == [
            ("a_file.py", 1, 0),
            ("a_file.py", 2, 0),
            ("z_file.py", 1, 0),
        ]
    finally:
        if os.path.exists(dest_dir):
            shutil.rmtree(dest_dir, ignore_errors=True)


def test_match_start_and_match_end_correctness(sample_repo):
    """18. match_start and match_end correctness."""
    repo_id, _ = sample_repo
    res = CodeSearchService.search_repository(repo_id, query="hello")

    for match in res.matches:
        extracted = match.line_content[match.match_start : match.match_end]
        assert extracted.lower() == "hello"


def test_line_numbers_are_1_indexed(sample_repo):
    """19. line numbers are 1-indexed."""
    repo_id, _ = sample_repo
    res = CodeSearchService.search_repository(repo_id, query="def hello_world")

    assert len(res.matches) == 1
    assert res.matches[0].line_number == 1


def test_repository_boundary_security(sample_repo):
    """20. repository boundary/security behavior."""
    repo_id, _ = sample_repo
    # Test path traversal in file_extension
    response = client.get(f"/api/repositories/{repo_id}/search?q=test&file_extension=../etc/passwd")
    assert response.status_code == 400
    assert "invalid file extension" in response.json()["detail"].lower()
