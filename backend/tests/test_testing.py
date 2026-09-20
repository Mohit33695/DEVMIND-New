"""
Tests for Testing Intelligence Service and API Endpoints.
"""

import os
import shutil
import zipfile
import pytest

from app.services.testing import CodeTestingService
from app.services.storage import RepositoryNotFoundError, RepositoryStorageService
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def cleanup_repo(repo_id: str):
    """Safely delete test repo directory from storage."""
    try:
        repo_dir = RepositoryStorageService.get_repository_directory(repo_id)
        if os.path.exists(repo_dir):
            shutil.rmtree(repo_dir, ignore_errors=True)
    except Exception:
        pass


def create_sample_zip(tmp_path, files_dict):
    """Helper to create a temporary zip file with a dict of filename -> content."""
    zip_path = tmp_path / "sample_test_repo.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        for fname, content in files_dict.items():
            zf.writestr(fname, content)
    return zip_path


def test_python_test_file_detection(tmp_path):
    files = {
        "app/service.py": "def add(a, b):\n    return a + b\n",
        "tests/test_service.py": "import pytest\n\ndef test_add():\n    assert add(1, 2) == 3\n",
    }
    zpath = create_sample_zip(tmp_path, files)
    with open(zpath, "rb") as f:
        repo_id, _ = RepositoryStorageService.store_repository_zip(f)

    try:
        resp = CodeTestingService.analyze_repository_testing(repo_id)
        assert resp.metrics.total_test_files == 1
        assert resp.test_files[0].file_path == "tests/test_service.py"
        assert resp.test_files[0].language == "Python"
        assert "pytest" in resp.metrics.detected_frameworks
    finally:
        cleanup_repo(repo_id)


def test_ts_js_test_file_detection(tmp_path):
    files = {
        "src/calculator.ts": "export function calc() { return 42; }",
        "src/calculator.test.ts": "import { vitest, expect, test } from 'vitest';\n test('calc test', () => { expect(calc()).toBe(42); });",
    }
    zpath = create_sample_zip(tmp_path, files)
    with open(zpath, "rb") as f:
        repo_id, _ = RepositoryStorageService.store_repository_zip(f)

    try:
        resp = CodeTestingService.analyze_repository_testing(repo_id)
        assert resp.metrics.total_test_files == 1
        assert "vitest" in resp.metrics.detected_frameworks
        assert resp.test_files[0].assertion_count >= 1
    finally:
        cleanup_repo(repo_id)


def test_java_go_test_file_detection(tmp_path):
    files = {
        "src/main/java/User.java": "public class User {}",
        "src/test/java/UserTest.java": "import org.junit.Test;\npublic class UserTest { @Test public void testUser() { assertEquals(1, 1); } }",
        "pkg/server.go": "package pkg\nfunc Run() {}",
        "pkg/server_test.go": "package pkg\nimport \"testing\"\nfunc TestRun(t *testing.T) { if false { t.Error(\"failed\") } }",
    }
    zpath = create_sample_zip(tmp_path, files)
    with open(zpath, "rb") as f:
        repo_id, _ = RepositoryStorageService.store_repository_zip(f)

    try:
        resp = CodeTestingService.analyze_repository_testing(repo_id)
        assert resp.metrics.total_test_files == 2
        assert "JUnit" in resp.metrics.detected_frameworks or "testing" in resp.metrics.detected_frameworks
    finally:
        cleanup_repo(repo_id)


def test_assertion_pattern_counting(tmp_path):
    files = {
        "tests/test_demo.py": "def test_multiple():\n    assert 1 == 1\n    assert 2 == 2\n    self.assertEqual(3, 3)\n",
    }
    zpath = create_sample_zip(tmp_path, files)
    with open(zpath, "rb") as f:
        repo_id, _ = RepositoryStorageService.store_repository_zip(f)

    try:
        resp = CodeTestingService.analyze_repository_testing(repo_id)
        assert resp.test_files[0].assertion_count == 3
    finally:
        cleanup_repo(repo_id)


def test_comment_and_doc_false_positives(tmp_path):
    files = {
        "README.md": "This markdown mentions assert and expect.",
        "tests/test_comments.py": "# assert 1 == 1 in comment\n# expect(1).toBe(1) in comment\ndef test_real():\n    # assert 2 == 2\n    pass\n",
    }
    zpath = create_sample_zip(tmp_path, files)
    with open(zpath, "rb") as f:
        repo_id, _ = RepositoryStorageService.store_repository_zip(f)

    try:
        resp = CodeTestingService.analyze_repository_testing(repo_id)
        # Markdown file should not be counted as test file
        assert resp.metrics.total_test_files == 1
        # Assertions inside comments must be ignored
        assert resp.test_files[0].assertion_count == 0
    finally:
        cleanup_repo(repo_id)


def test_source_to_test_mapping(tmp_path):
    files = {
        "src/auth.py": "def login(): pass",
        "tests/test_auth.py": "def test_login(): assert True",
        "src/payment.py": "def pay(): pass",
    }
    zpath = create_sample_zip(tmp_path, files)
    with open(zpath, "rb") as f:
        repo_id, _ = RepositoryStorageService.store_repository_zip(f)

    try:
        resp = CodeTestingService.analyze_repository_testing(repo_id)
        mappings = {m.source_file: m for m in resp.source_mappings}
        assert mappings["src/auth.py"].has_obvious_test is True
        assert mappings["src/auth.py"].matching_test_file == "tests/test_auth.py"
        assert mappings["src/auth.py"].confidence == "HIGH"

        assert mappings["src/payment.py"].has_obvious_test is False
        assert mappings["src/payment.py"].confidence == "NONE"
    finally:
        cleanup_repo(repo_id)


def test_empty_repository(tmp_path):
    files = {
        "README.md": "Just documentation",
        "src/util.py": "def util(): pass",
    }
    zpath = create_sample_zip(tmp_path, files)
    with open(zpath, "rb") as f:
        repo_id, _ = RepositoryStorageService.store_repository_zip(f)

    try:
        resp = CodeTestingService.analyze_repository_testing(repo_id)
        assert resp.metrics.total_test_files == 0
        assert resp.metrics.estimated_test_ratio == 0.0
    finally:
        cleanup_repo(repo_id)


def test_repository_not_found():
    with pytest.raises(RepositoryNotFoundError):
        CodeTestingService.analyze_repository_testing("invalid-uuid-99999")


def test_api_testing_endpoint(tmp_path):
    files = {
        "src/math.py": "def double(x): return x * 2",
        "tests/test_math.py": "import pytest\ndef test_double(): assert double(2) == 4",
    }
    zpath = create_sample_zip(tmp_path, files)
    with open(zpath, "rb") as f:
        repo_id, _ = RepositoryStorageService.store_repository_zip(f)

    try:
        response = client.get(f"/api/repositories/{repo_id}/testing")
        assert response.status_code == 200
        data = response.json()
        assert data["repo_id"] == repo_id
        assert data["metrics"]["total_test_files"] == 1
        assert len(data["test_files"]) == 1
        assert len(data["source_mappings"]) == 1
    finally:
        cleanup_repo(repo_id)
