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


def test_list_repositories_api():
    """Verifies that GET /api/repositories returns stored repositories list."""
    zip_bytes = create_sample_zip()
    upload_resp = client.post(
        "/api/repositories/upload",
        files={"file": ("list_test.zip", zip_bytes, "application/zip")},
    )
    assert upload_resp.status_code == 200
    repo_id = upload_resp.json()["repo_id"]

    response = client.get("/api/repositories")
    assert response.status_code == 200
    repos = response.json()
    assert isinstance(repos, list)
    matching = [r for r in repos if r["repo_id"] == repo_id]
    assert len(matching) == 1
    assert matching[0]["filename"] == "list_test.zip"
    assert matching[0]["total_files"] == 2
    assert "Python" in matching[0]["detected_languages"]
    assert "indexing_status" in matching[0]


def test_get_repository_detail_api_success():
    """Verifies GET /api/repositories/{repo_id} returns metadata and reconstructed file tree."""
    zip_bytes = create_sample_zip()
    upload_resp = client.post(
        "/api/repositories/upload",
        files={"file": ("detail_test.zip", zip_bytes, "application/zip")},
    )
    repo_id = upload_resp.json()["repo_id"]

    response = client.get(f"/api/repositories/{repo_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["repo_id"] == repo_id
    assert data["filename"] == "detail_test.zip"
    assert "scan_result" in data
    assert data["scan_result"]["total_files"] == 2
    assert "src/main.py" in data["scan_result"]["scanned_files"]
    assert "README.md" in data["scan_result"]["scanned_files"]


def test_get_repository_detail_api_not_found():
    """Verifies GET /api/repositories/{repo_id} returns 404 for unknown repository."""
    response = client.get("/api/repositories/unknown-repo-id-404")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_get_repository_detail_api_path_traversal():
    """Verifies GET /api/repositories/{repo_id} rejects path traversal."""
    response = client.get("/api/repositories/../../etc")
    # FastAPI path parser might return 400, 404, or route error
    assert response.status_code in (400, 404)


def test_delete_repository_api_success():
    """Verifies DELETE /api/repositories/{repo_id} removes repo and vector index."""
    zip_bytes = create_sample_zip()
    upload_resp = client.post(
        "/api/repositories/upload",
        files={"file": ("to_delete.zip", zip_bytes, "application/zip")},
    )
    repo_id = upload_resp.json()["repo_id"]

    # Verify exists
    assert client.get(f"/api/repositories/{repo_id}").status_code == 200

    # Delete
    del_resp = client.delete(f"/api/repositories/{repo_id}")
    assert del_resp.status_code == 200
    assert del_resp.json()["deleted"] is True

    # Verify now 404
    assert client.get(f"/api/repositories/{repo_id}").status_code == 404


def test_delete_repository_api_not_found():
    """Verifies DELETE /api/repositories/{repo_id} returns 404 for non-existent repo."""
    response = client.delete("/api/repositories/non-existent-uuid-999")
    assert response.status_code == 404


def test_corrupted_metadata_handling():
    """Verifies that missing or corrupted metadata is handled safely by list and detail endpoints."""
    import os

    zip_bytes = create_sample_zip()
    upload_resp = client.post(
        "/api/repositories/upload",
        files={"file": ("corrupt_test.zip", zip_bytes, "application/zip")},
    )
    repo_id = upload_resp.json()["repo_id"]

    # Deliberately corrupt .devmind_meta.json
    from app.services.storage import RepositoryStorageService

    repo_dir = RepositoryStorageService.get_repository_directory(repo_id)
    meta_path = os.path.join(repo_dir, RepositoryStorageService.META_FILENAME)
    with open(meta_path, "w", encoding="utf-8") as f:
        f.write("{corrupted json content")

    # Verify list endpoint recovers gracefully
    list_resp = client.get("/api/repositories")
    assert list_resp.status_code == 200
    repos = list_resp.json()
    matching = [r for r in repos if r["repo_id"] == repo_id]
    assert len(matching) == 1
    assert matching[0]["total_files"] == 2

    # Verify detail endpoint recovers gracefully
    detail_resp = client.get(f"/api/repositories/{repo_id}")
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert detail["repo_id"] == repo_id
    assert detail["scan_result"]["total_files"] == 2

    # Cleanup
    client.delete(f"/api/repositories/{repo_id}")


def test_cross_repository_access_isolation():
    """Verifies that no repository can access or delete another repository's files."""
    zip_bytes = create_sample_zip()

    # Create Repo A
    resp_a = client.post(
        "/api/repositories/upload",
        files={"file": ("repo_a.zip", zip_bytes, "application/zip")},
    )
    repo_a = resp_a.json()["repo_id"]

    # Create Repo B
    resp_b = client.post(
        "/api/repositories/upload",
        files={"file": ("repo_b.zip", zip_bytes, "application/zip")},
    )
    repo_b = resp_b.json()["repo_b_id"] if "repo_b_id" in resp_b.json() else resp_b.json()["repo_id"]

    # Attempt to access Repo B file through Repo A using path traversal
    traverse_path = f"../../{repo_b}/src/main.py"
    leak_resp = client.get(f"/api/repositories/{repo_a}/files/content", params={"path": traverse_path})
    assert leak_resp.status_code == 400
    assert "path traversal" in leak_resp.json()["detail"].lower()

    # Attempt to delete Repo B via path traversal in repo_id parameter
    del_traverse = client.delete(f"/api/repositories/../{repo_b}")
    assert del_traverse.status_code in (400, 404)

    # Verify Repo B still exists intact
    detail_b = client.get(f"/api/repositories/{repo_b}")
    assert detail_b.status_code == 200

    # Cleanup both repositories cleanly
    client.delete(f"/api/repositories/{repo_a}")
    client.delete(f"/api/repositories/{repo_b}")


def test_delete_repository_cleans_vector_index():
    """Verifies that deleting a repository also removes its vector index."""
    zip_bytes = create_sample_zip()
    upload_resp = client.post(
        "/api/repositories/upload",
        files={"file": ("rag_delete.zip", zip_bytes, "application/zip")},
    )
    repo_id = upload_resp.json()["repo_id"]

    # Index repository
    index_resp = client.post(f"/api/repositories/{repo_id}/index")
    assert index_resp.status_code == 200
    assert index_resp.json()["status"] == "indexed"

    # Status check confirms indexed
    status_resp = client.get(f"/api/repositories/{repo_id}/index/status")
    assert status_resp.status_code == 200
    assert status_resp.json()["status"] == "indexed"

    # Delete repository
    del_resp = client.delete(f"/api/repositories/{repo_id}")
    assert del_resp.status_code == 200

    # Verify vector status check now raises 404 because repo was deleted
    post_status = client.get(f"/api/repositories/{repo_id}/index/status")
    assert post_status.status_code == 404

