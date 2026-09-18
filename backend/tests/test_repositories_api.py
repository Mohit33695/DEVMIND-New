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
