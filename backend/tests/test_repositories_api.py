"""
Integration tests for repository upload API route and health endpoint.
"""

import io
import zipfile
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def create_sample_zip() -> bytes:
    """Creates a sample valid zip archive buffer."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        zf.writestr("src/main.py", "print('hello devmind')")
        zf.writestr("README.md", "# DevMind App")
    return buffer.getvalue()


def test_health_check_endpoint():
    """Verifies that GET /api/health returns operational status."""
    response = client.get("/api/health")
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["status"] == "ok"
    assert json_data["service"] == "DevMind AI backend"


def test_upload_repository_success():
    """Verifies that POST /api/repositories/upload accepts a valid ZIP and returns scan metadata."""
    zip_bytes = create_sample_zip()
    files = {"file": ("test_repo.zip", zip_bytes, "application/zip")}

    response = client.post("/api/repositories/upload", files=files)
    assert response.status_code == 200
    data = response.json()

    assert data["filename"] == "test_repo.zip"
    assert data["status"] == "validated"
    assert "repo_id" in data and isinstance(data["repo_id"], str)
    assert "scan_result" in data
    assert data["scan_result"]["total_files"] == 2
    assert data["scan_result"]["detected_languages"]["Python"] == 1
    assert data["scan_result"]["detected_languages"]["Markdown"] == 1



def test_upload_invalid_file_extension():
    """Verifies that uploading non-zip file returns 400 Bad Request."""
    files = {"file": ("invalid.txt", b"plain text content", "text/plain")}
    response = client.post("/api/repositories/upload", files=files)
    assert response.status_code == 400
    assert "Invalid file format" in response.json()["detail"]


def test_upload_malicious_zip_traversal():
    """Verifies that uploading a zip with path traversal returns 400 Bad Request."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        zf.writestr("../evil.txt", "hacked")
    malicious_bytes = buffer.getvalue()

    files = {"file": ("malicious.zip", malicious_bytes, "application/zip")}
    response = client.post("/api/repositories/upload", files=files)
    assert response.status_code == 400
    assert "path traversal" in response.json()["detail"].lower()


def test_get_file_content_api_success():
    """Verifies that GET /api/repositories/{repo_id}/files/content returns file text."""
    zip_bytes = create_sample_zip()
    upload_resp = client.post("/api/repositories/upload", files={"file": ("repo.zip", zip_bytes, "application/zip")})
    assert upload_resp.status_code == 200
    repo_id = upload_resp.json()["repo_id"]

    content_resp = client.get(f"/api/repositories/{repo_id}/files/content", params={"path": "src/main.py"})
    assert content_resp.status_code == 200
    data = content_resp.json()
    assert data["repo_id"] == repo_id
    assert data["path"] == "src/main.py"
    assert data["content"] == "print('hello devmind')"
    assert data["encoding"] == "utf-8"


def test_get_file_content_api_repo_not_found():
    """Verifies 404 response when repo_id does not exist."""
    response = client.get("/api/repositories/invalid-repo-uuid/files/content", params={"path": "main.py"})
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_get_file_content_api_file_not_found():
    """Verifies 404 response when file path does not exist in repo."""
    zip_bytes = create_sample_zip()
    upload_resp = client.post("/api/repositories/upload", files={"file": ("repo.zip", zip_bytes, "application/zip")})
    repo_id = upload_resp.json()["repo_id"]

    response = client.get(f"/api/repositories/{repo_id}/files/content", params={"path": "non_existent.py"})
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_get_file_content_api_path_traversal():
    """Verifies 400 response when path attempts path traversal."""
    zip_bytes = create_sample_zip()
    upload_resp = client.post("/api/repositories/upload", files={"file": ("repo.zip", zip_bytes, "application/zip")})
    repo_id = upload_resp.json()["repo_id"]

    response = client.get(f"/api/repositories/{repo_id}/files/content", params={"path": "../../etc/passwd"})
    assert response.status_code == 400
    assert "path traversal" in response.json()["detail"].lower()

