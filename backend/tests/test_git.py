"""
Tests for Git Intelligence Service and API Endpoints.
"""

import os
import shutil
import zipfile
import pytest
import git

from app.services.git import CodeGitService
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


def test_repo_without_git_metadata(tmp_path):
    zip_path = tmp_path / "no_git_repo.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("app/main.py", "print('hello')")

    with open(zip_path, "rb") as f:
        repo_id, _ = RepositoryStorageService.store_repository_zip(f)

    try:
        resp = CodeGitService.analyze_repository_git(repo_id)
        assert resp.summary.has_git_metadata is False
        assert resp.summary.analyzed_commit_count == 0
        assert resp.commits == []
        assert resp.contributors == []
    finally:
        cleanup_repo(repo_id)


def test_repo_with_git_metadata(tmp_path):
    # Create a local Git repository dynamically in tmp_path
    git_repo_dir = tmp_path / "git_source"
    os.makedirs(git_repo_dir, exist_ok=True)

    repo = git.Repo.init(git_repo_dir)

    # Configure committer
    with repo.config_writer() as config:
        config.set_value("user", "name", "Alice Dev")
        config.set_value("user", "email", "alice@example.com")

    # Create Commit 1
    file1 = git_repo_dir / "service.py"
    file1.write_text("def run(): pass\n")
    repo.index.add(["service.py"])
    commit1 = repo.index.commit("Initial commit - added service")

    # Create Commit 2
    file2 = git_repo_dir / "utils.py"
    file2.write_text("def helper(): pass\n")
    file1.write_text("def run(): print('updated')\n")
    repo.index.add(["utils.py", "service.py"])
    commit2 = repo.index.commit("Second commit - updated service and added utils")

    # Package into ZIP including .git
    zip_path = tmp_path / "git_repo.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        for root, dirs, files in os.walk(git_repo_dir):
            for file in files:
                abs_f = os.path.join(root, file)
                rel_f = os.path.relpath(abs_f, git_repo_dir)
                zf.write(abs_f, rel_f)

    with open(zip_path, "rb") as f:
        repo_id, _ = RepositoryStorageService.store_repository_zip(f)

    try:
        resp = CodeGitService.analyze_repository_git(repo_id)
        assert resp.summary.has_git_metadata is True
        assert resp.summary.analyzed_commit_count == 2
        assert len(resp.commits) == 2
        assert resp.commits[0].message == "Second commit - updated service and added utils"
        assert resp.commits[0].author_name == "Alice Dev"
        assert resp.commits[0].author_email == "alice@example.com"

        # Check contributors
        assert len(resp.contributors) == 1
        assert resp.contributors[0].name == "Alice Dev"
        assert resp.contributors[0].commit_count == 2

        # Check file hotspots
        hotspot_paths = [h.file_path for h in resp.top_changed_files]
        assert "service.py" in hotspot_paths
        assert "utils.py" in hotspot_paths
        # service.py changed in 2 commits
        service_hotspot = next(h for h in resp.top_changed_files if h.file_path == "service.py")
        assert service_hotspot.commit_count == 2
    finally:
        cleanup_repo(repo_id)


def test_max_commits_bounding(tmp_path):
    git_repo_dir = tmp_path / "git_source_max"
    os.makedirs(git_repo_dir, exist_ok=True)
    repo = git.Repo.init(git_repo_dir)
    with repo.config_writer() as config:
        config.set_value("user", "name", "Bob Tester")
        config.set_value("user", "email", "bob@example.com")

    for i in range(5):
        f = git_repo_dir / f"file_{i}.txt"
        f.write_text(f"content {i}")
        repo.index.add([f"file_{i}.txt"])
        repo.index.commit(f"Commit #{i}")

    zip_path = tmp_path / "git_max.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        for root, dirs, files in os.walk(git_repo_dir):
            for file in files:
                abs_f = os.path.join(root, file)
                rel_f = os.path.relpath(abs_f, git_repo_dir)
                zf.write(abs_f, rel_f)

    with open(zip_path, "rb") as f:
        repo_id, _ = RepositoryStorageService.store_repository_zip(f)

    try:
        # Request max_commits = 2
        resp = CodeGitService.analyze_repository_git(repo_id, max_commits=2)
        assert resp.summary.analyzed_commit_count == 2
        assert len(resp.commits) == 2
    finally:
        cleanup_repo(repo_id)


def test_commit_message_truncation(tmp_path):
    git_repo_dir = tmp_path / "git_source_trunc"
    os.makedirs(git_repo_dir, exist_ok=True)
    repo = git.Repo.init(git_repo_dir)
    with repo.config_writer() as config:
        config.set_value("user", "name", "Carol")
        config.set_value("user", "email", "carol@example.com")

    long_msg = "X" * 300
    f = git_repo_dir / "test.txt"
    f.write_text("data")
    repo.index.add(["test.txt"])
    repo.index.commit(long_msg)

    zip_path = tmp_path / "git_trunc.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        for root, dirs, files in os.walk(git_repo_dir):
            for file in files:
                abs_f = os.path.join(root, file)
                rel_f = os.path.relpath(abs_f, git_repo_dir)
                zf.write(abs_f, rel_f)

    with open(zip_path, "rb") as f:
        repo_id, _ = RepositoryStorageService.store_repository_zip(f)

    try:
        resp = CodeGitService.analyze_repository_git(repo_id)
        assert len(resp.commits[0].message) <= 250
    finally:
        cleanup_repo(repo_id)


def test_security_boundary_no_hook_execution(tmp_path):
    """Explicitly verifies that Git Intelligence DOES NOT execute hooks inside .git/hooks/."""
    git_repo_dir = tmp_path / "git_source_security"
    os.makedirs(git_repo_dir, exist_ok=True)
    repo = git.Repo.init(git_repo_dir)

    # 1. Create normal commit first
    f = git_repo_dir / "safe.py"
    f.write_text("print('safe')")
    repo.index.add(["safe.py"])
    repo.index.commit("Safe commit")

    # 2. Plant malicious hook AFTER commit creation
    marker_file = tmp_path / "HOOK_EXECUTIVE_MARKER.txt"
    hooks_dir = git_repo_dir / ".git" / "hooks"
    os.makedirs(hooks_dir, exist_ok=True)
    hook_file = hooks_dir / "post-checkout"
    hook_script = f"#!/bin/sh\necho 'EXECUTED' > '{marker_file}'\n"
    hook_file.write_text(hook_script)

    # Make executable if supported
    try:
        os.chmod(hook_file, 0o777)
    except Exception:
        pass

    # Package into zip
    zip_path = tmp_path / "git_sec.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        for root, dirs, files in os.walk(git_repo_dir):
            for file in files:
                abs_f = os.path.join(root, file)
                rel_f = os.path.relpath(abs_f, git_repo_dir)
                zf.write(abs_f, rel_f)

    with open(zip_path, "rb") as f:
        repo_id, _ = RepositoryStorageService.store_repository_zip(f)

    try:
        resp = CodeGitService.analyze_repository_git(repo_id)
        assert resp.summary.has_git_metadata is True
        # VERIFY MARKER FILE WAS NOT CREATED
        assert not os.path.exists(marker_file), "SECURITY VULNERABILITY: Git hook was executed during Git Intelligence analysis!"
    finally:
        cleanup_repo(repo_id)


def test_repository_not_found():
    with pytest.raises(RepositoryNotFoundError):
        CodeGitService.analyze_repository_git("invalid-uuid-99999")


def test_api_git_endpoint(tmp_path):
    git_repo_dir = tmp_path / "git_api"
    os.makedirs(git_repo_dir, exist_ok=True)
    repo = git.Repo.init(git_repo_dir)
    with repo.config_writer() as config:
        config.set_value("user", "name", "Dave")
        config.set_value("user", "email", "dave@example.com")

    f = git_repo_dir / "code.py"
    f.write_text("x = 1")
    repo.index.add(["code.py"])
    repo.index.commit("API Test Commit")

    zip_path = tmp_path / "git_api.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        for root, dirs, files in os.walk(git_repo_dir):
            for file in files:
                abs_f = os.path.join(root, file)
                rel_f = os.path.relpath(abs_f, git_repo_dir)
                zf.write(abs_f, rel_f)

    with open(zip_path, "rb") as f:
        repo_id, _ = RepositoryStorageService.store_repository_zip(f)

    try:
        response = client.get(f"/api/repositories/{repo_id}/git?max_commits=10")
        assert response.status_code == 200
        data = response.json()
        assert data["repo_id"] == repo_id
        assert data["summary"]["has_git_metadata"] is True
        assert data["summary"]["analyzed_commit_count"] == 1
        assert len(data["commits"]) == 1
    finally:
        cleanup_repo(repo_id)
