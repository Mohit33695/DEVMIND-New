"""
Tests for Persistent Vector Store, Disk Lifecycle, Concurrency, and RAG Integration (Milestone AA.4).
"""

import json
import os
import shutil
import threading
import zipfile
import pytest

from app.schemas.rag import CodeChunk
from app.services.embeddings import MockEmbeddingProvider
from app.services.rag import CodebaseRAGService
from app.services.storage import RepositoryStorageService
from app.services.vector_store import (
    InMemoryVectorStore,
    PersistentVectorStore,
    global_vector_store,
)


def create_test_zip(tmp_path, files_dict):
    zip_path = tmp_path / "test_aa4_repo.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        for fname, content in files_dict.items():
            zf.writestr(fname, content)
    return zip_path


def cleanup_repo(repo_id: str):
    try:
        global_vector_store.delete_repository_vectors(repo_id)
        if repo_id in CodebaseRAGService._status_cache:
            del CodebaseRAGService._status_cache[repo_id]
        repo_dir = RepositoryStorageService.get_repository_directory(repo_id)
        if os.path.exists(repo_dir):
            shutil.rmtree(repo_dir, ignore_errors=True)
    except Exception:
        pass


# -----------------------------------------------------------------------------
# 1. Persistence & Lifecycle Tests (1 to 4, 19, 20)
# -----------------------------------------------------------------------------
def test_vectors_survive_store_recreation(tmp_path):
    repo_id = "repo-persist-1"
    repo_dir = tmp_path / repo_id
    repo_dir.mkdir(parents=True, exist_ok=True)

    with pytest.MonkeyPatch.context() as m:
        m.setattr(RepositoryStorageService, "get_repository_directory", lambda r_id: str(tmp_path / r_id))

        store1 = PersistentVectorStore()
        chunk = CodeChunk(
            chunk_id="c1",
            repo_id=repo_id,
            file_path="main.py",
            language="Python",
            start_line=1,
            end_line=5,
            content="print(1)",
            content_hash="h1",
        )
        store1.add_chunks(repo_id, [chunk], [[0.1] * 384])
        store1.set_repository_metadata(repo_id, "mock", "mock", 384)

        # Confirm index.json file was written to disk
        index_file = repo_dir / "index.json"
        assert index_file.exists()

        # Recreate store instance (simulating backend restart)
        store2 = PersistentVectorStore()
        assert store2.has_repository(repo_id) is True
        assert store2.get_repository_chunk_count(repo_id) == 1

        hits = store2.search(repo_id, [0.1] * 384, top_k=5)
        assert len(hits) == 1
        assert hits[0][0].chunk_id == "c1"


def test_persistent_index_survives_cache_reset(tmp_path):
    repo_id = "repo-persist-cache"
    repo_dir = tmp_path / repo_id
    repo_dir.mkdir(parents=True, exist_ok=True)

    with pytest.MonkeyPatch.context() as m:
        m.setattr(RepositoryStorageService, "get_repository_directory", lambda r_id: str(tmp_path / r_id))

        store = PersistentVectorStore()
        chunk = CodeChunk(
            chunk_id="c2",
            repo_id=repo_id,
            file_path="app.py",
            language="Python",
            start_line=1,
            end_line=2,
            content="val = 42",
            content_hash="h2",
        )
        store.add_chunks(repo_id, [chunk], [[0.5] * 384])
        store.set_repository_metadata(repo_id, "mock", "mock", 384)

        # Manually clear in-memory cache map
        store._storage.clear()
        store._metadata.clear()

        # Must reload transparently from disk
        meta = store.get_repository_metadata(repo_id)
        assert meta is not None
        assert meta["provider"] == "mock"
        assert store.get_repository_chunk_count(repo_id) == 1


def test_repository_isolation(tmp_path):
    repo_a = "repo-iso-A"
    repo_b = "repo-iso-B"
    (tmp_path / repo_a).mkdir(parents=True, exist_ok=True)
    (tmp_path / repo_b).mkdir(parents=True, exist_ok=True)

    with pytest.MonkeyPatch.context() as m:
        m.setattr(RepositoryStorageService, "get_repository_directory", lambda r_id: str(tmp_path / r_id))

        store = PersistentVectorStore()
        chunk_a = CodeChunk(
            chunk_id="ca",
            repo_id=repo_a,
            file_path="a.py",
            language="Python",
            start_line=1,
            end_line=2,
            content="code a",
            content_hash="ha",
        )
        chunk_b = CodeChunk(
            chunk_id="cb",
            repo_id=repo_b,
            file_path="b.py",
            language="Python",
            start_line=1,
            end_line=2,
            content="code b",
            content_hash="hb",
        )

        store.add_chunks(repo_a, [chunk_a], [[0.1] * 384])
        store.add_chunks(repo_b, [chunk_b], [[0.9] * 384])

        # Confirm on-disk isolation: repo-a has index.json, repo-b has index.json
        assert (tmp_path / repo_a / "index.json").exists()
        assert (tmp_path / repo_b / "index.json").exists()

        # Query repo-A -> must NEVER return repo-B vectors!
        results_a = store.search(repo_a, [0.1] * 384)
        assert len(results_a) == 1
        assert results_a[0][0].repo_id == repo_a


def test_metadata_persistence(tmp_path):
    repo_id = "repo-meta-persist"
    (tmp_path / repo_id).mkdir(parents=True, exist_ok=True)

    with pytest.MonkeyPatch.context() as m:
        m.setattr(RepositoryStorageService, "get_repository_directory", lambda r_id: str(tmp_path / r_id))

        store1 = PersistentVectorStore()
        store1.set_repository_metadata(repo_id, "OpenAIEmbeddingProvider (text-embedding-3-small)", "text-embedding-3-small", 1536)

        store2 = PersistentVectorStore()
        meta = store2.get_repository_metadata(repo_id)
        assert meta is not None
        assert meta["provider"] == "OpenAIEmbeddingProvider (text-embedding-3-small)"
        assert meta["model"] == "text-embedding-3-small"
        assert meta["dimension"] == 1536
        assert "updated_at" in meta


# -----------------------------------------------------------------------------
# 2. Configuration Mismatch & Re-index Tests (5 to 8)
# -----------------------------------------------------------------------------
def test_provider_mismatch(tmp_path):
    files = {"calc.py": "x = 1\n"}
    zpath = create_test_zip(tmp_path, files)
    with open(zpath, "rb") as f:
        repo_id, _ = RepositoryStorageService.store_repository_zip(f)

    try:
        # Index with default mock provider
        CodebaseRAGService.index_repository(repo_id)

        # Simulate backend restart by clearing cache & setting active provider env
        CodebaseRAGService._status_cache.clear()

        with pytest.MonkeyPatch.context() as m:
            m.setenv("EMBEDDING_PROVIDER", "openai")
            m.setenv("OPENAI_API_KEY", "sk-test")

            with pytest.raises(ValueError) as exc:
                CodebaseRAGService.retrieve_codebase_context(repo_id, "x")
            assert "requires re-indexing" in str(exc.value)
    finally:
        cleanup_repo(repo_id)


def test_model_mismatch(tmp_path):
    files = {"calc.py": "x = 1\n"}
    zpath = create_test_zip(tmp_path, files)
    with open(zpath, "rb") as f:
        repo_id, _ = RepositoryStorageService.store_repository_zip(f)

    try:
        CodebaseRAGService.index_repository(repo_id)

        with pytest.MonkeyPatch.context() as m:
            m.setenv("EMBEDDING_MODEL", "model-v2")

            with pytest.raises(ValueError) as exc:
                CodebaseRAGService.retrieve_codebase_context(repo_id, "x")
            assert "requires re-indexing" in str(exc.value)
    finally:
        cleanup_repo(repo_id)


def test_dimension_mismatch(tmp_path):
    files = {"calc.py": "x = 1\n"}
    zpath = create_test_zip(tmp_path, files)
    with open(zpath, "rb") as f:
        repo_id, _ = RepositoryStorageService.store_repository_zip(f)

    try:
        CodebaseRAGService.index_repository(repo_id)

        with pytest.MonkeyPatch.context() as m:
            m.setenv("EMBEDDING_DIMENSION", "512")

            with pytest.raises(ValueError) as exc:
                CodebaseRAGService.retrieve_codebase_context(repo_id, "x")
            assert "requires re-indexing" in str(exc.value)
    finally:
        cleanup_repo(repo_id)


def test_explicit_reindex_requirement(tmp_path):
    files = {"main.py": "def test(): pass\n"}
    zpath = create_test_zip(tmp_path, files)
    with open(zpath, "rb") as f:
        repo_id, _ = RepositoryStorageService.store_repository_zip(f)

    try:
        CodebaseRAGService.index_repository(repo_id)
        index_count = 0
        orig_idx = CodebaseRAGService.index_repository

        def spy_idx(r_id):
            nonlocal index_count
            index_count += 1
            return orig_idx(r_id)

        with pytest.MonkeyPatch.context() as m:
            m.setenv("EMBEDDING_MODEL", "new-model")
            m.setattr(CodebaseRAGService, "index_repository", spy_idx)

            with pytest.raises(ValueError):
                CodebaseRAGService.retrieve_codebase_context(repo_id, "test")

            # Must NOT call index_repository automatically
            assert index_count == 0
    finally:
        cleanup_repo(repo_id)


# -----------------------------------------------------------------------------
# 3. Deletion, Cleanup, & Failure Recovery Tests (9 to 11)
# -----------------------------------------------------------------------------
def test_delete_repository_vectors(tmp_path):
    repo_id = "repo-del-disk"
    repo_dir = tmp_path / repo_id
    repo_dir.mkdir(parents=True, exist_ok=True)

    with pytest.MonkeyPatch.context() as m:
        m.setattr(RepositoryStorageService, "get_repository_directory", lambda r_id: str(tmp_path / r_id))

        store = PersistentVectorStore()
        chunk = CodeChunk(
            chunk_id="cdel",
            repo_id=repo_id,
            file_path="f.py",
            language="Python",
            start_line=1,
            end_line=2,
            content="val",
            content_hash="hdel",
        )
        store.add_chunks(repo_id, [chunk], [[0.1] * 384])
        assert (repo_dir / "index.json").exists()

        store.delete_repository_vectors(repo_id)
        assert not (repo_dir / "index.json").exists()
        assert store.has_repository(repo_id) is False


def test_partial_indexing_cleanup(tmp_path):
    repo_id = "repo-partial-cleanup"
    repo_dir = tmp_path / repo_id
    repo_dir.mkdir(parents=True, exist_ok=True)

    with pytest.MonkeyPatch.context() as m:
        m.setattr(RepositoryStorageService, "get_repository_directory", lambda r_id: str(tmp_path / r_id))

        store = PersistentVectorStore()
        # Simulate partial temp file
        tmp_file = repo_dir / "index.json.tmp"
        tmp_file.write_text("partial data", encoding="utf-8")

        store.delete_repository_vectors(repo_id)
        assert not tmp_file.exists()


def test_failed_indexing_recovery(tmp_path):
    files = {"calc.py": "def calc(): return 1\n"}
    zpath = create_test_zip(tmp_path, files)
    with open(zpath, "rb") as f:
        repo_id, _ = RepositoryStorageService.store_repository_zip(f)

    try:
        # Index successfully
        st1 = CodebaseRAGService.index_repository(repo_id)
        assert st1.status == "indexed"

        # Verify disk index exists
        repo_dir = RepositoryStorageService.get_repository_directory(repo_id)
        assert os.path.exists(os.path.join(repo_dir, "index.json"))

        # Re-index successfully
        st2 = CodebaseRAGService.index_repository(repo_id)
        assert st2.status == "indexed"
    finally:
        cleanup_repo(repo_id)


# -----------------------------------------------------------------------------
# 4. Retrieval, Threshold, & Concurrency Tests (12 to 18)
# -----------------------------------------------------------------------------
def test_top_k_retrieval(tmp_path):
    repo_id = "repo-top-k"
    (tmp_path / repo_id).mkdir(parents=True, exist_ok=True)

    with pytest.MonkeyPatch.context() as m:
        m.setattr(RepositoryStorageService, "get_repository_directory", lambda r_id: str(tmp_path / r_id))

        store = PersistentVectorStore()
        chunks = [
            CodeChunk(
                chunk_id=f"c_{i}",
                repo_id=repo_id,
                file_path=f"file_{i}.py",
                language="Python",
                start_line=1,
                end_line=2,
                content=f"code {i}",
                content_hash=f"h_{i}",
            )
            for i in range(10)
        ]
        embeddings = [[float(i) / 10.0] * 384 for i in range(10)]
        store.add_chunks(repo_id, chunks, embeddings)

        results = store.search(repo_id, [0.5] * 384, top_k=3)
        assert len(results) == 3


def test_score_threshold(tmp_path):
    repo_id = "repo-score-thresh"
    (tmp_path / repo_id).mkdir(parents=True, exist_ok=True)

    with pytest.MonkeyPatch.context() as m:
        m.setattr(RepositoryStorageService, "get_repository_directory", lambda r_id: str(tmp_path / r_id))

        store = PersistentVectorStore()
        chunk = CodeChunk(
            chunk_id="c_thresh",
            repo_id=repo_id,
            file_path="file.py",
            language="Python",
            start_line=1,
            end_line=2,
            content="code",
            content_hash="h",
        )
        store.add_chunks(repo_id, [chunk], [[0.0] * 384])

        # Query with orthogonal vector -> similarity ~ 0.0
        results = store.search(repo_id, [1.0] * 384, score_threshold=0.8)
        assert len(results) == 0


def test_empty_repository(tmp_path):
    repo_id = "repo-empty"
    (tmp_path / repo_id).mkdir(parents=True, exist_ok=True)

    with pytest.MonkeyPatch.context() as m:
        m.setattr(RepositoryStorageService, "get_repository_directory", lambda r_id: str(tmp_path / r_id))

        store = PersistentVectorStore()
        assert store.has_repository(repo_id) is False
        assert store.get_repository_chunk_count(repo_id) == 0
        assert store.search(repo_id, [0.1] * 384) == []


def test_missing_repository():
    store = PersistentVectorStore()
    assert store.has_repository("non-existent-uuid-999") is False
    assert store.get_repository_metadata("non-existent-uuid-999") is None


def test_concurrent_indexing_safety(tmp_path):
    repo_id = "repo-concurrent-write"
    (tmp_path / repo_id).mkdir(parents=True, exist_ok=True)

    with pytest.MonkeyPatch.context() as m:
        m.setattr(RepositoryStorageService, "get_repository_directory", lambda r_id: str(tmp_path / r_id))

        store = PersistentVectorStore()
        errors = []

        def worker(idx):
            try:
                chunk = CodeChunk(
                    chunk_id=f"c_thread_{idx}",
                    repo_id=repo_id,
                    file_path=f"thread_{idx}.py",
                    language="Python",
                    start_line=1,
                    end_line=2,
                    content=f"print({idx})",
                    content_hash=f"h_thread_{idx}",
                )
                store.add_chunks(repo_id, [chunk], [[0.1 * idx] * 384])
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert (tmp_path / repo_id / "index.json").exists()


def test_corrupted_index_handling(tmp_path):
    repo_id = "repo-corrupted-json"
    repo_dir = tmp_path / repo_id
    repo_dir.mkdir(parents=True, exist_ok=True)

    # Write broken JSON payload to index.json
    index_file = repo_dir / "index.json"
    index_file.write_text("{corrupted: json string ...", encoding="utf-8")

    with pytest.MonkeyPatch.context() as m:
        m.setattr(RepositoryStorageService, "get_repository_directory", lambda r_id: str(tmp_path / r_id))

        store = PersistentVectorStore()
        # Should not crash backend; returns False gracefully
        assert store.has_repository(repo_id) is False
        assert store.search(repo_id, [0.1] * 384) == []


def test_persistent_storage_path_safety():
    store = PersistentVectorStore()
    # Path traversal attempts return None
    assert store._get_index_filepath("../../etc/passwd") is None
    assert store._get_index_filepath("../relative") is None
