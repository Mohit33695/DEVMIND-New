"""
Integration tests for GET /api/repositories/{repo_id}/symbols API route.
"""

import io
import zipfile
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def create_python_repo_zip() -> bytes:
    """Creates a sample zip archive containing Python files with functions, classes, and imports."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        zf.writestr(
            "app/main.py",
            "import sys\n\ndef start_server():\n    \"\"\"Start main server.\"\"\"\n    pass\n",
        )
        zf.writestr(
            "app/models.py",
            "class DatabaseModel:\n    \"\"\"Base DB Model.\"\"\"\n    def save(self):\n        pass\n",
        )
        zf.writestr("README.md", "# DevMind Docs")
    return buffer.getvalue()


def test_get_repository_symbols_success():
    """Verifies that GET /api/repositories/{repo_id}/symbols extracts and returns symbol metadata."""
    zip_bytes = create_python_repo_zip()
    upload_resp = client.post(
        "/api/repositories/upload",
        files={"file": ("python_repo.zip", zip_bytes, "application/zip")},
    )
    assert upload_resp.status_code == 200
    repo_id = upload_resp.json()["repo_id"]

    symbols_resp = client.get(f"/api/repositories/{repo_id}/symbols")
    assert symbols_resp.status_code == 200

    data = symbols_resp.json()
    assert data["repo_id"] == repo_id
    assert data["total_symbols"] > 0
    assert len(data["file_symbols"]) == 2  # app/main.py and app/models.py

    paths = [f["file_path"] for f in data["file_symbols"]]
    assert "app/main.py" in paths
    assert "app/models.py" in paths

    main_symbols = next(f["symbols"] for f in data["file_symbols"] if f["file_path"] == "app/main.py")
    main_names = [s["name"] for s in main_symbols]
    assert "import sys" in main_names
    assert "start_server" in main_names


def test_get_repository_symbols_multi_language():
    """Verifies symbol extraction for repositories containing both Python and TypeScript files."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        zf.writestr("server.py", "def run(): pass\n")
        zf.writestr("client.ts", "import axios from 'axios';\nexport class ApiClient {}\n")
        zf.writestr("config.json", '{"env": "prod"}')

    zip_bytes = buffer.getvalue()
    upload_resp = client.post(
        "/api/repositories/upload",
        files={"file": ("multi_repo.zip", zip_bytes, "application/zip")},
    )
    assert upload_resp.status_code == 200
    repo_id = upload_resp.json()["repo_id"]

    symbols_resp = client.get(f"/api/repositories/{repo_id}/symbols")
    assert symbols_resp.status_code == 200

    data = symbols_resp.json()
    assert data["repo_id"] == repo_id
    assert len(data["file_symbols"]) == 2  # server.py and client.ts (config.json skipped)

    paths = [f["file_path"] for f in data["file_symbols"]]
    assert "server.py" in paths
    assert "client.ts" in paths

    ts_file = next(f for f in data["file_symbols"] if f["file_path"] == "client.ts")
    assert ts_file["language"] == "TypeScript"
    assert len(ts_file["symbols"]) == 2


def test_get_repository_symbols_not_found():
    """Verifies 404 response when repo_id does not exist."""
    response = client.get("/api/repositories/non-existent-uuid-12345/symbols")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()

