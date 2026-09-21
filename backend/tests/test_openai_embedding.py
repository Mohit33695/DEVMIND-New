"""
Tests for OpenAI Embedding Provider, Factory Resolution, Safety, Security, and RAG Integration (Milestone AA.2).
"""

import json
import zipfile
import pytest
import httpx

from app.core.config import Settings, UnsupportedProviderError
from app.schemas.rag import CodeChunk
from app.services.embeddings import (
    EmbeddingAuthError,
    EmbeddingDimensionMismatchError,
    EmbeddingNetworkError,
    EmbeddingProvider,
    EmbeddingRateLimitError,
    EmbeddingResponseError,
    EmbeddingTimeoutError,
    MockEmbeddingProvider,
    get_embedding_provider,
)
from app.services.providers.openai_embedding import OpenAIEmbeddingProvider
from app.services.rag import CodebaseRAGService, sanitize_error_message
from app.services.storage import RepositoryStorageService
from app.services.vector_store import global_vector_store


# Helper function for test zip creation
def create_test_zip(tmp_path, files_dict):
    zip_path = tmp_path / "test_aa2_repo.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        for fname, content in files_dict.items():
            zf.writestr(fname, content)
    return zip_path


def cleanup_repo(repo_id: str):
    try:
        global_vector_store.delete_repository_vectors(repo_id)
        if repo_id in CodebaseRAGService._status_cache:
            del CodebaseRAGService._status_cache[repo_id]
    except Exception:
        pass


# -----------------------------------------------------------------------------
# 1. Factory / Unit Tests (1 to 9)
# -----------------------------------------------------------------------------
def test_mock_provider_unchanged():
    provider = get_embedding_provider("mock")
    assert isinstance(provider, MockEmbeddingProvider)
    assert provider.get_dimension() == 384
    assert "MockEmbeddingProvider" in provider.get_provider_name()


def test_mock_provider_deterministic():
    provider = MockEmbeddingProvider(dimension=384)
    vec1 = provider.embed_texts(["hello world"])[0]
    vec2 = provider.embed_texts(["hello world"])[0]
    assert vec1 == vec2


def test_openai_provider_resolves(monkeypatch):
    monkeypatch.setenv("EMBEDDING_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key-12345")
    provider = get_embedding_provider()
    assert isinstance(provider, OpenAIEmbeddingProvider)
    assert provider.get_dimension() == 384
    assert "OpenAIEmbeddingProvider" in provider.get_provider_name()


def test_missing_openai_api_key_fails(monkeypatch):
    monkeypatch.setenv("EMBEDDING_PROVIDER", "openai")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(UnsupportedProviderError) as exc_info:
        get_embedding_provider()
    assert "OPENAI_API_KEY is not configured" in str(exc_info.value)


def test_unsupported_provider_fails():
    with pytest.raises(UnsupportedProviderError) as exc_info:
        get_embedding_provider("unknown_provider")
    assert "Unsupported embedding provider" in str(exc_info.value)


def test_empty_input_returns_empty():
    provider = OpenAIEmbeddingProvider(
        api_key="sk-test",
        model="text-embedding-3-small",
        dimension=1536,
    )
    res = provider.embed_texts([])
    assert res == []


def test_whitespace_handling():
    def mock_handler(request: httpx.Request) -> httpx.Response:
        data = json.loads(request.content)
        count = len(data["input"])
        resp_data = [
            {"embedding": [0.1] * 1536, "index": i} for i in range(count)
        ]
        return httpx.Response(200, json={"data": resp_data})

    transport = httpx.MockTransport(mock_handler)
    provider = OpenAIEmbeddingProvider(
        api_key="sk-test",
        model="text-embedding-3-small",
        dimension=1536,
        transport=transport,
    )
    vectors = provider.embed_texts(["   ", "\n\t"])
    assert len(vectors) == 2
    assert len(vectors[0]) == 1536


def test_provider_name_format():
    provider = OpenAIEmbeddingProvider(
        api_key="sk-test",
        model="text-embedding-3-small",
        dimension=1536,
    )
    assert provider.get_provider_name() == "OpenAIEmbeddingProvider (text-embedding-3-small)"


def test_configured_dimension():
    provider = OpenAIEmbeddingProvider(
        api_key="sk-test",
        model="text-embedding-3-small",
        dimension=768,
    )
    assert provider.get_dimension() == 768


# -----------------------------------------------------------------------------
# 2. HTTP Behavior Tests (10 to 24)
# -----------------------------------------------------------------------------
def test_successful_embedding_response():
    def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "data": [
                    {"embedding": [0.5, 0.25], "index": 0}
                ]
            },
        )

    transport = httpx.MockTransport(mock_handler)
    provider = OpenAIEmbeddingProvider(
        api_key="sk-test",
        model="custom-model",
        dimension=2,
        transport=transport,
    )
    vectors = provider.embed_texts(["hello"])
    assert vectors == [[0.5, 0.25]]


def test_correct_authorization_header():
    captured_headers = {}

    def mock_handler(request: httpx.Request) -> httpx.Response:
        nonlocal captured_headers
        captured_headers = dict(request.headers)
        return httpx.Response(
            200,
            json={"data": [{"embedding": [0.1] * 384, "index": 0}]},
        )

    transport = httpx.MockTransport(mock_handler)
    provider = OpenAIEmbeddingProvider(
        api_key="sk-secret-key-999",
        model="mock",
        dimension=384,
        transport=transport,
    )
    provider.embed_texts(["test"])
    assert captured_headers.get("authorization") == "Bearer sk-secret-key-999"


def test_correct_model_in_payload():
    captured_payload = {}

    def mock_handler(request: httpx.Request) -> httpx.Response:
        nonlocal captured_payload
        captured_payload = json.loads(request.content)
        return httpx.Response(
            200,
            json={"data": [{"embedding": [0.1] * 1536, "index": 0}]},
        )

    transport = httpx.MockTransport(mock_handler)
    provider = OpenAIEmbeddingProvider(
        api_key="sk-test",
        model="text-embedding-3-small",
        dimension=1536,
        transport=transport,
    )
    provider.embed_texts(["sample text"])
    assert captured_payload.get("model") == "text-embedding-3-small"
    assert captured_payload.get("dimensions") == 1536


def test_correct_endpoint():
    captured_url = None

    def mock_handler(request: httpx.Request) -> httpx.Response:
        nonlocal captured_url
        captured_url = str(request.url)
        return httpx.Response(
            200,
            json={"data": [{"embedding": [0.1] * 384, "index": 0}]},
        )

    transport = httpx.MockTransport(mock_handler)
    provider = OpenAIEmbeddingProvider(
        api_key="sk-test",
        model="mock",
        dimension=384,
        base_url="https://api.openai.com/v1",
        transport=transport,
    )
    provider.embed_texts(["test"])
    assert captured_url == "https://api.openai.com/v1/embeddings"


def test_batching_250_texts_to_3_requests():
    request_counts = []

    def mock_handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        inputs = body["input"]
        request_counts.append(len(inputs))
        resp_data = [{"embedding": [0.1] * 384, "index": i} for i in range(len(inputs))]
        return httpx.Response(200, json={"data": resp_data})

    transport = httpx.MockTransport(mock_handler)
    provider = OpenAIEmbeddingProvider(
        api_key="sk-test",
        model="mock",
        dimension=384,
        batch_size=100,
        transport=transport,
    )
    texts = [f"text_{i}" for i in range(250)]
    results = provider.embed_texts(texts)

    assert len(results) == 250
    assert request_counts == [100, 100, 50]


def test_returned_order_preserved():
    def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "data": [
                    {"embedding": [0.2, 0.2], "index": 1},
                    {"embedding": [0.1, 0.1], "index": 0},
                ]
            },
        )

    transport = httpx.MockTransport(mock_handler)
    provider = OpenAIEmbeddingProvider(
        api_key="sk-test",
        model="mock",
        dimension=2,
        transport=transport,
    )
    res = provider.embed_texts(["first", "second"])
    assert res == [[0.1, 0.1], [0.2, 0.2]]


def test_count_mismatch_raises_error():
    def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"data": [{"embedding": [0.1] * 384, "index": 0}]},
        )

    transport = httpx.MockTransport(mock_handler)
    provider = OpenAIEmbeddingProvider(
        api_key="sk-test",
        model="mock",
        dimension=384,
        transport=transport,
    )
    with pytest.raises(EmbeddingResponseError) as exc:
        provider.embed_texts(["a", "b"])
    assert "Embedding count mismatch" in str(exc.value)


def test_malformed_response_structure():
    def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"unexpected": "structure"})

    transport = httpx.MockTransport(mock_handler)
    provider = OpenAIEmbeddingProvider(
        api_key="sk-test",
        model="mock",
        dimension=384,
        transport=transport,
    )
    with pytest.raises(EmbeddingResponseError):
        provider.embed_texts(["a"])


def test_malformed_vector_non_numeric():
    def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"data": [{"embedding": ["not", "numeric"], "index": 0}]},
        )

    transport = httpx.MockTransport(mock_handler)
    provider = OpenAIEmbeddingProvider(
        api_key="sk-test",
        model="mock",
        dimension=2,
        transport=transport,
    )
    with pytest.raises(EmbeddingResponseError) as exc:
        provider.embed_texts(["a"])
    assert "non-numeric" in str(exc.value)


def test_dimension_mismatch():
    def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"data": [{"embedding": [0.1, 0.2], "index": 0}]},
        )

    transport = httpx.MockTransport(mock_handler)
    provider = OpenAIEmbeddingProvider(
        api_key="sk-test",
        model="mock",
        dimension=384,
        transport=transport,
    )
    with pytest.raises(EmbeddingDimensionMismatchError) as exc:
        provider.embed_texts(["a"])
    assert "dimension mismatch" in str(exc.value)


def test_http_401_auth_error():
    def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": {"message": "Invalid API Key"}})

    transport = httpx.MockTransport(mock_handler)
    provider = OpenAIEmbeddingProvider(
        api_key="sk-invalid",
        model="mock",
        dimension=384,
        transport=transport,
    )
    with pytest.raises(EmbeddingAuthError):
        provider.embed_texts(["test"])


def test_http_429_rate_limit_error():
    def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json={"error": {"message": "Rate limit exceeded"}})

    transport = httpx.MockTransport(mock_handler)
    provider = OpenAIEmbeddingProvider(
        api_key="sk-test",
        model="mock",
        dimension=384,
        transport=transport,
    )
    with pytest.raises(EmbeddingRateLimitError):
        provider.embed_texts(["test"])


def test_http_500_503_server_error():
    def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, text="Service Unavailable")

    transport = httpx.MockTransport(mock_handler)
    provider = OpenAIEmbeddingProvider(
        api_key="sk-test",
        model="mock",
        dimension=384,
        transport=transport,
    )
    with pytest.raises(EmbeddingResponseError) as exc:
        provider.embed_texts(["test"])
    assert "503" in str(exc.value)


def test_network_failure():
    def mock_handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("Connection refused")

    transport = httpx.MockTransport(mock_handler)
    provider = OpenAIEmbeddingProvider(
        api_key="sk-test",
        model="mock",
        dimension=384,
        transport=transport,
    )
    with pytest.raises(EmbeddingNetworkError):
        provider.embed_texts(["test"])


def test_timeout():
    def mock_handler(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("Request timed out")

    transport = httpx.MockTransport(mock_handler)
    provider = OpenAIEmbeddingProvider(
        api_key="sk-test",
        model="mock",
        dimension=384,
        transport=transport,
    )
    with pytest.raises(EmbeddingTimeoutError):
        provider.embed_texts(["test"])


# -----------------------------------------------------------------------------
# 3. Security Tests (25 to 27)
# -----------------------------------------------------------------------------
def test_api_key_never_in_exception():
    secret_key = "sk-super-secret-token-123456789"

    def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, text=f"Unauthorized call with key {secret_key}")

    transport = httpx.MockTransport(mock_handler)
    provider = OpenAIEmbeddingProvider(
        api_key=secret_key,
        model="mock",
        dimension=384,
        transport=transport,
    )
    with pytest.raises(EmbeddingAuthError) as exc:
        provider.embed_texts(["test"])
    assert secret_key not in str(exc.value)


def test_api_key_never_in_index_status(tmp_path):
    secret_key = "sk-secret-key-embedded-123"
    files = {"main.py": "print('hello')"}
    zpath = create_test_zip(tmp_path, files)

    with open(zpath, "rb") as f:
        repo_id, _ = RepositoryStorageService.store_repository_zip(f)

    try:
        def mock_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(401, json={"error": f"Invalid key {secret_key}"})

        transport = httpx.MockTransport(mock_handler)
        test_provider = OpenAIEmbeddingProvider(
            api_key=secret_key,
            model="text-embedding-3-small",
            dimension=1536,
            transport=transport,
        )

        with pytest.MonkeyPatch.context() as m:
            m.setenv("EMBEDDING_PROVIDER", "openai")
            m.setenv("OPENAI_API_KEY", secret_key)
            m.setattr(CodebaseRAGService, "get_embedding_provider", lambda: test_provider)

            status = CodebaseRAGService.index_repository(repo_id)
            assert status.status == "failed"
            assert secret_key not in (status.error or "")
    finally:
        cleanup_repo(repo_id)


def test_authorization_header_never_in_logs_or_errors():
    raw_error_text = "Failed request with Bearer sk-secret-token-abc"
    sanitized = sanitize_error_message(raw_error_text)
    assert "sk-secret-token-abc" not in sanitized
    assert "Bearer [REDACTED]" in sanitized


# -----------------------------------------------------------------------------
# 4. RAG Integration Tests (28 to 35)
# -----------------------------------------------------------------------------
def test_rag_indexing_with_mocked_openai_provider(tmp_path):
    files = {"src/utils.py": "def add(a, b):\n    return a + b\n"}
    zpath = create_test_zip(tmp_path, files)

    with open(zpath, "rb") as f:
        repo_id, _ = RepositoryStorageService.store_repository_zip(f)

    try:
        def mock_handler(request: httpx.Request) -> httpx.Response:
            data = json.loads(request.content)
            count = len(data["input"])
            return httpx.Response(
                200,
                json={
                    "data": [
                        {"embedding": [0.1] * 1536, "index": i}
                        for i in range(count)
                    ]
                },
            )

        transport = httpx.MockTransport(mock_handler)
        test_provider = OpenAIEmbeddingProvider(
            api_key="sk-valid-key",
            model="text-embedding-3-small",
            dimension=1536,
            transport=transport,
        )

        with pytest.MonkeyPatch.context() as m:
            m.setenv("EMBEDDING_PROVIDER", "openai")
            m.setenv("OPENAI_API_KEY", "sk-valid-key")
            m.setenv("EMBEDDING_MODEL", "text-embedding-3-small")
            m.setenv("EMBEDDING_DIMENSION", "1536")
            m.setattr(CodebaseRAGService, "get_embedding_provider", lambda: test_provider)

            status = CodebaseRAGService.index_repository(repo_id)
            assert status.status == "indexed"
            assert status.total_chunks > 0
            assert status.embedding_dimension == 1536
    finally:
        cleanup_repo(repo_id)


def test_repository_isolation():
    chunk_a = CodeChunk(
        chunk_id="c1",
        repo_id="repo-A",
        file_path="a.py",
        language="Python",
        start_line=1,
        end_line=2,
        content="code a",
        content_hash="h1",
    )
    chunk_b = CodeChunk(
        chunk_id="c2",
        repo_id="repo-B",
        file_path="b.py",
        language="Python",
        start_line=1,
        end_line=2,
        content="code b",
        content_hash="h2",
    )

    global_vector_store.add_chunks("repo-A", [chunk_a], [[0.1] * 384])
    global_vector_store.add_chunks("repo-B", [chunk_b], [[0.9] * 384])

    results = global_vector_store.search("repo-A", [0.1] * 384, top_k=5)
    assert len(results) == 1
    assert results[0][0].repo_id == "repo-A"

    cleanup_repo("repo-A")
    cleanup_repo("repo-B")


def test_failed_indexing_leaves_no_partial_vectors(tmp_path):
    files = {"calc.py": "def calc(): return 42\n"}
    zpath = create_test_zip(tmp_path, files)

    with open(zpath, "rb") as f:
        repo_id, _ = RepositoryStorageService.store_repository_zip(f)

    try:
        def mock_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(500, text="Internal Server Error")

        transport = httpx.MockTransport(mock_handler)
        test_provider = OpenAIEmbeddingProvider(
            api_key="sk-valid-key",
            model="text-embedding-3-small",
            dimension=1536,
            transport=transport,
        )

        with pytest.MonkeyPatch.context() as m:
            m.setenv("EMBEDDING_PROVIDER", "openai")
            m.setenv("OPENAI_API_KEY", "sk-valid-key")
            m.setattr(CodebaseRAGService, "get_embedding_provider", lambda: test_provider)

            status = CodebaseRAGService.index_repository(repo_id)
            assert status.status == "failed"
            assert global_vector_store.has_repository(repo_id) is False
            assert global_vector_store.get_repository_chunk_count(repo_id) == 0
    finally:
        cleanup_repo(repo_id)


def test_retry_after_failure(tmp_path):
    files = {"app.py": "print('retry test')\n"}
    zpath = create_test_zip(tmp_path, files)

    with open(zpath, "rb") as f:
        repo_id, _ = RepositoryStorageService.store_repository_zip(f)

    try:
        call_count = 0

        def mock_handler(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return httpx.Response(500, text="Server Error")
            return httpx.Response(
                200,
                json={"data": [{"embedding": [0.1] * 384, "index": 0}]},
            )

        transport = httpx.MockTransport(mock_handler)
        test_provider = OpenAIEmbeddingProvider(
            api_key="sk-valid-key",
            model="mock",
            dimension=384,
            transport=transport,
        )

        with pytest.MonkeyPatch.context() as m:
            m.setenv("EMBEDDING_PROVIDER", "openai")
            m.setenv("OPENAI_API_KEY", "sk-valid-key")
            m.setattr(CodebaseRAGService, "get_embedding_provider", lambda: test_provider)

            # 1. First attempt fails
            st1 = CodebaseRAGService.index_repository(repo_id)
            assert st1.status == "failed"

            # 2. Retry succeeds
            st2 = CodebaseRAGService.index_repository(repo_id)
            assert st2.status == "indexed"
            assert st2.total_chunks > 0
    finally:
        cleanup_repo(repo_id)


def test_provider_metadata_stored(tmp_path):
    files = {"index.py": "x = 1\n"}
    zpath = create_test_zip(tmp_path, files)

    with open(zpath, "rb") as f:
        repo_id, _ = RepositoryStorageService.store_repository_zip(f)

    try:
        CodebaseRAGService.index_repository(repo_id)
        meta = global_vector_store.get_repository_metadata(repo_id)
        assert meta is not None
        assert "provider" in meta
        assert "model" in meta
        assert "dimension" in meta
    finally:
        cleanup_repo(repo_id)


def test_model_mismatch_detected(tmp_path):
    files = {"main.py": "val = 100\n"}
    zpath = create_test_zip(tmp_path, files)

    with open(zpath, "rb") as f:
        repo_id, _ = RepositoryStorageService.store_repository_zip(f)

    try:
        # Index under mock provider / mock model
        CodebaseRAGService.index_repository(repo_id)

        with pytest.MonkeyPatch.context() as m:
            # Change active model setting
            m.setenv("EMBEDDING_MODEL", "different-model-name")

            with pytest.raises(ValueError) as exc:
                CodebaseRAGService.retrieve_codebase_context(
                    repo_id=repo_id, query="val"
                )
            assert "requires re-indexing" in str(exc.value)
    finally:
        cleanup_repo(repo_id)


def test_dimension_mismatch_detected(tmp_path):
    files = {"main.py": "val = 100\n"}
    zpath = create_test_zip(tmp_path, files)

    with open(zpath, "rb") as f:
        repo_id, _ = RepositoryStorageService.store_repository_zip(f)

    try:
        # Index under 384 dim
        CodebaseRAGService.index_repository(repo_id)

        with pytest.MonkeyPatch.context() as m:
            # Change dimension setting
            m.setenv("EMBEDDING_DIMENSION", "512")

            with pytest.raises(ValueError) as exc:
                CodebaseRAGService.retrieve_codebase_context(
                    repo_id=repo_id, query="val"
                )
            assert "requires re-indexing" in str(exc.value)
    finally:
        cleanup_repo(repo_id)


def test_mismatch_does_not_trigger_auto_reindex(tmp_path):
    files = {"main.py": "val = 100\n"}
    zpath = create_test_zip(tmp_path, files)

    with open(zpath, "rb") as f:
        repo_id, _ = RepositoryStorageService.store_repository_zip(f)

    try:
        CodebaseRAGService.index_repository(repo_id)

        index_calls = 0
        orig_index = CodebaseRAGService.index_repository

        def spy_index(r_id):
            nonlocal index_calls
            index_calls += 1
            return orig_index(r_id)

        with pytest.MonkeyPatch.context() as m:
            m.setenv("EMBEDDING_MODEL", "model-changed")
            m.setattr(CodebaseRAGService, "index_repository", spy_index)

            with pytest.raises(ValueError):
                CodebaseRAGService.retrieve_codebase_context(
                    repo_id=repo_id, query="val"
                )

            # Confirm index_repository was NOT called automatically
            assert index_calls == 0
    finally:
        cleanup_repo(repo_id)
