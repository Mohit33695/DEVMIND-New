"""
Tests for OpenAI LLM Provider, Factory Resolution, Safety, Security, and Chat Pipeline (Milestone AA.3).
"""

import json
import zipfile
import pytest
import httpx

from app.core.config import UnsupportedProviderError
from app.schemas.chat import ChatMessage, ChatRequest
from app.services.chat import CodebaseChatService
from app.services.context import ContextBuilder
from app.services.llm import (
    LLMAuthError,
    LLMNetworkError,
    LLMProvider,
    LLMRateLimitError,
    LLMResponseError,
    LLMTimeoutError,
    MockLLMProvider,
    get_llm_provider,
)
from app.services.providers.openai_llm import OpenAILLMProvider
from app.services.rag import CodebaseRAGService, sanitize_error_message
from app.services.storage import RepositoryStorageService
from app.services.vector_store import global_vector_store


def create_test_zip(tmp_path, files_dict):
    zip_path = tmp_path / "test_aa3_repo.zip"
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
# 1. Factory / Unit Tests (1 to 5, 29)
# -----------------------------------------------------------------------------
def test_mock_llm_provider_unchanged():
    provider = get_llm_provider("mock")
    assert isinstance(provider, MockLLMProvider)
    assert "MockLLMProvider" in provider.get_provider_name()

    resp = provider.generate_response(
        system_instruction="sys",
        user_message="test",
        grounded_context="File: main.py\n```\nprint(1)\n```",
    )
    assert resp.grounded is True
    assert "DevMind AI Grounded Analysis" in resp.answer


def test_mock_factory_resolution():
    provider = get_llm_provider("mock")
    assert isinstance(provider, MockLLMProvider)


def test_openai_factory_resolution(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-llm-key")
    provider = get_llm_provider()
    assert isinstance(provider, OpenAILLMProvider)
    assert "OpenAILLMProvider" in provider.get_provider_name()


def test_missing_api_key_fails(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(UnsupportedProviderError) as exc:
        get_llm_provider()
    assert "OPENAI_API_KEY is not configured" in str(exc.value)


def test_unsupported_provider_fails():
    with pytest.raises(UnsupportedProviderError) as exc:
        get_llm_provider("unsupported_llm")
    assert "Unsupported LLM provider" in str(exc.value)


def test_factory_makes_zero_network_requests(monkeypatch):
    # Pass an invalid endpoint URL to verify factory performs no HTTP calls
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-valid-key")
    monkeypatch.setenv("LLM_API_BASE_URL", "https://invalid-host-that-does-not-exist.test")

    # Should succeed instantly without network exceptions
    provider = get_llm_provider()
    assert isinstance(provider, OpenAILLMProvider)


# -----------------------------------------------------------------------------
# 2. HTTP Behavior & Completion Tests (6 to 12)
# -----------------------------------------------------------------------------
def test_successful_completion():
    def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": "The calculate_total function computes order cost.",
                        }
                    }
                ]
            },
        )

    transport = httpx.MockTransport(mock_handler)
    provider = OpenAILLMProvider(
        api_key="sk-test",
        model="gpt-4o-mini",
        transport=transport,
    )
    resp = provider.generate_response(
        system_instruction="System instruction",
        user_message="How does total work?",
        grounded_context="File: order.py\ndef calculate_total(): pass",
    )
    assert resp.answer == "The calculate_total function computes order cost."
    assert resp.grounded is True
    assert resp.model_name == "gpt-4o-mini"
    assert "OpenAILLMProvider" in resp.provider_name


def test_correct_endpoint():
    captured_url = None

    def mock_handler(request: httpx.Request) -> httpx.Response:
        nonlocal captured_url
        captured_url = str(request.url)
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "ok"}}]},
        )

    transport = httpx.MockTransport(mock_handler)
    provider = OpenAILLMProvider(
        api_key="sk-test",
        model="gpt-4o-mini",
        base_url="https://api.openai.com/v1",
        transport=transport,
    )
    provider.generate_response("sys", "user msg", "context")
    assert captured_url == "https://api.openai.com/v1/chat/completions"


def test_correct_authorization_header():
    captured_headers = {}

    def mock_handler(request: httpx.Request) -> httpx.Response:
        nonlocal captured_headers
        captured_headers = dict(request.headers)
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "ok"}}]},
        )

    transport = httpx.MockTransport(mock_handler)
    provider = OpenAILLMProvider(
        api_key="sk-llm-secret-999",
        model="gpt-4o-mini",
        transport=transport,
    )
    provider.generate_response("sys", "user msg", "context")
    assert captured_headers.get("authorization") == "Bearer sk-llm-secret-999"


def test_correct_model():
    captured_payload = {}

    def mock_handler(request: httpx.Request) -> httpx.Response:
        nonlocal captured_payload
        captured_payload = json.loads(request.content)
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "ok"}}]},
        )

    transport = httpx.MockTransport(mock_handler)
    provider = OpenAILLMProvider(
        api_key="sk-test",
        model="custom-llm-model-v2",
        transport=transport,
    )
    provider.generate_response("sys", "user msg", "context")
    assert captured_payload.get("model") == "custom-llm-model-v2"
    assert captured_payload.get("temperature") == 0.0


def test_correct_max_tokens():
    captured_payload = {}

    def mock_handler(request: httpx.Request) -> httpx.Response:
        nonlocal captured_payload
        captured_payload = json.loads(request.content)
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "ok"}}]},
        )

    transport = httpx.MockTransport(mock_handler)
    provider = OpenAILLMProvider(
        api_key="sk-test",
        model="gpt-4o-mini",
        max_tokens=2048,
        transport=transport,
    )
    provider.generate_response("sys", "user msg", "context")
    assert captured_payload.get("max_tokens") == 2048


def test_correct_message_construction():
    captured_payload = {}

    def mock_handler(request: httpx.Request) -> httpx.Response:
        nonlocal captured_payload
        captured_payload = json.loads(request.content)
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "ok"}}]},
        )

    transport = httpx.MockTransport(mock_handler)
    provider = OpenAILLMProvider(
        api_key="sk-test",
        model="gpt-4o-mini",
        transport=transport,
    )
    provider.generate_response(
        system_instruction="Strict Security System Prompt",
        user_message="Explain login()",
        grounded_context="File: auth.py\ndef login(): pass",
    )
    messages = captured_payload.get("messages", [])
    assert len(messages) >= 2
    assert messages[0]["role"] == "system"
    assert messages[0]["content"] == "Strict Security System Prompt"
    assert messages[-1]["role"] == "user"
    assert "<untrusted_repository_context>" in messages[-1]["content"]
    assert "Explain login()" in messages[-1]["content"]


def test_history_formatting():
    captured_payload = {}

    def mock_handler(request: httpx.Request) -> httpx.Response:
        nonlocal captured_payload
        captured_payload = json.loads(request.content)
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "ok"}}]},
        )

    transport = httpx.MockTransport(mock_handler)
    provider = OpenAILLMProvider(
        api_key="sk-test",
        model="gpt-4o-mini",
        transport=transport,
    )
    history = [
        ChatMessage(role="user", content="Prev Q1"),
        ChatMessage(role="assistant", content="Prev A1"),
    ]
    provider.generate_response(
        system_instruction="Sys",
        user_message="Current Q",
        grounded_context="ctx",
        history=history,
    )
    messages = captured_payload.get("messages", [])
    assert len(messages) == 4
    assert messages[1] == {"role": "user", "content": "Prev Q1"}
    assert messages[2] == {"role": "assistant", "content": "Prev A1"}


# -----------------------------------------------------------------------------
# 3. Response Validation Tests (13 to 17)
# -----------------------------------------------------------------------------
def test_empty_response():
    def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "   "}}]},
        )

    transport = httpx.MockTransport(mock_handler)
    provider = OpenAILLMProvider(
        api_key="sk-test",
        model="gpt-4o-mini",
        transport=transport,
    )
    resp = provider.generate_response("sys", "user msg", "context")
    assert "insufficient evidence" in resp.answer or "no additional synthesis" in resp.answer


def test_malformed_json():
    def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="Not JSON payload")

    transport = httpx.MockTransport(mock_handler)
    provider = OpenAILLMProvider(api_key="sk-test", model="gpt-4o-mini", transport=transport)
    with pytest.raises(LLMResponseError) as exc:
        provider.generate_response("sys", "msg", "ctx")
    assert "invalid JSON" in str(exc.value)


def test_missing_choices():
    def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"unexpected": 123})

    transport = httpx.MockTransport(mock_handler)
    provider = OpenAILLMProvider(api_key="sk-test", model="gpt-4o-mini", transport=transport)
    with pytest.raises(LLMResponseError) as exc:
        provider.generate_response("sys", "msg", "ctx")
    assert "missing choices array" in str(exc.value)


def test_missing_message():
    def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": [{}]})

    transport = httpx.MockTransport(mock_handler)
    provider = OpenAILLMProvider(api_key="sk-test", model="gpt-4o-mini", transport=transport)
    with pytest.raises(LLMResponseError) as exc:
        provider.generate_response("sys", "msg", "ctx")
    assert "invalid choice message structure" in str(exc.value)


def test_non_string_content():
    def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": [{"message": {"content": 12345}}]})

    transport = httpx.MockTransport(mock_handler)
    provider = OpenAILLMProvider(api_key="sk-test", model="gpt-4o-mini", transport=transport)
    with pytest.raises(LLMResponseError) as exc:
        provider.generate_response("sys", "msg", "ctx")
    assert "non-string message content" in str(exc.value)


# -----------------------------------------------------------------------------
# 4. HTTP Error Mapping Tests (18 to 23)
# -----------------------------------------------------------------------------
def test_http_401():
    def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": "Unauthorized key"})

    transport = httpx.MockTransport(mock_handler)
    provider = OpenAILLMProvider(api_key="sk-invalid", model="gpt-4o-mini", transport=transport)
    with pytest.raises(LLMAuthError):
        provider.generate_response("sys", "msg", "ctx")


def test_http_429():
    def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json={"error": "Rate limit exceeded"})

    transport = httpx.MockTransport(mock_handler)
    provider = OpenAILLMProvider(api_key="sk-test", model="gpt-4o-mini", transport=transport)
    with pytest.raises(LLMRateLimitError):
        provider.generate_response("sys", "msg", "ctx")


def test_http_500():
    def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="Internal Server Error")

    transport = httpx.MockTransport(mock_handler)
    provider = OpenAILLMProvider(api_key="sk-test", model="gpt-4o-mini", transport=transport)
    with pytest.raises(LLMResponseError) as exc:
        provider.generate_response("sys", "msg", "ctx")
    assert "500" in str(exc.value)


def test_http_503():
    def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, text="Service Unavailable")

    transport = httpx.MockTransport(mock_handler)
    provider = OpenAILLMProvider(api_key="sk-test", model="gpt-4o-mini", transport=transport)
    with pytest.raises(LLMResponseError) as exc:
        provider.generate_response("sys", "msg", "ctx")
    assert "503" in str(exc.value)


def test_network_failure():
    def mock_handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("Connection refused")

    transport = httpx.MockTransport(mock_handler)
    provider = OpenAILLMProvider(api_key="sk-test", model="gpt-4o-mini", transport=transport)
    with pytest.raises(LLMNetworkError):
        provider.generate_response("sys", "msg", "ctx")


def test_timeout():
    def mock_handler(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("Request timed out")

    transport = httpx.MockTransport(mock_handler)
    provider = OpenAILLMProvider(api_key="sk-test", model="gpt-4o-mini", transport=transport)
    with pytest.raises(LLMTimeoutError):
        provider.generate_response("sys", "msg", "ctx")


# -----------------------------------------------------------------------------
# 5. Security & Redaction Tests (24, 30)
# -----------------------------------------------------------------------------
def test_api_key_redaction():
    secret_key = "sk-secret-llm-token-123456789"

    def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, text=f"Call failed for key {secret_key}")

    transport = httpx.MockTransport(mock_handler)
    provider = OpenAILLMProvider(api_key=secret_key, model="gpt-4o-mini", transport=transport)
    with pytest.raises(LLMAuthError) as exc:
        provider.generate_response("sys", "msg", "ctx")
    assert secret_key not in str(exc.value)


def test_no_secret_leakage_in_returned_error():
    raw_error_text = "Call failed with Bearer sk-secret-token-abc"
    sanitized = sanitize_error_message(raw_error_text)
    assert "sk-secret-token-abc" not in sanitized
    assert "Bearer [REDACTED]" in sanitized


# -----------------------------------------------------------------------------
# 6. Chat Service & Prompt Integration Tests (25 to 28)
# -----------------------------------------------------------------------------
def test_provider_failure_through_chat_service(tmp_path):
    files = {"src/app.py": "def run(): pass\n"}
    zpath = create_test_zip(tmp_path, files)

    with open(zpath, "rb") as f:
        repo_id, _ = RepositoryStorageService.store_repository_zip(f)

    try:
        # Index repo first
        CodebaseRAGService.index_repository(repo_id)

        def mock_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(500, text="LLM Error")

        transport = httpx.MockTransport(mock_handler)
        test_provider = OpenAILLMProvider(
            api_key="sk-valid-key",
            model="gpt-4o-mini",
            transport=transport,
        )

        with pytest.MonkeyPatch.context() as m:
            m.setattr(CodebaseChatService, "_llm_provider", test_provider)

            req = ChatRequest(message="explain run")
            with pytest.raises(LLMResponseError):
                CodebaseChatService.chat_with_repository(repo_id, req)
    finally:
        cleanup_repo(repo_id)


def test_repository_isolation(tmp_path):
    files_a = {"repo_a.py": "def secret_a(): pass\n"}
    zpath_a = create_test_zip(tmp_path, files_a)
    with open(zpath_a, "rb") as f:
        repo_a_id, _ = RepositoryStorageService.store_repository_zip(f)

    files_b = {"repo_b.py": "def secret_b(): pass\n"}
    zpath_b = create_test_zip(tmp_path, files_b)
    with open(zpath_b, "rb") as f:
        repo_b_id, _ = RepositoryStorageService.store_repository_zip(f)

    try:
        CodebaseRAGService.index_repository(repo_a_id)
        CodebaseRAGService.index_repository(repo_b_id)

        # Retrieve context for repo_a_id -> should only contain repo_a.py
        ret_a = CodebaseRAGService.retrieve_codebase_context(repo_a_id, "secret")
        for res in ret_a.results:
            assert res.chunk.repo_id == repo_a_id
            assert res.chunk.file_path == "repo_a.py"
    finally:
        cleanup_repo(repo_a_id)
        cleanup_repo(repo_b_id)


def test_prompt_boundary_preservation():
    full_prompt = ContextBuilder.build_full_prompt(
        user_message="What does compute() do?",
        formatted_context="File: math.py\ndef compute(): return 42",
    )
    assert "<untrusted_repository_context>" in full_prompt
    assert "</untrusted_repository_context>" in full_prompt
    assert "User Question: What does compute() do?" in full_prompt


def test_bounded_history():
    history_items = [
        ChatMessage(role="user" if i % 2 == 0 else "assistant", content=f"msg_{i}")
        for i in range(15)
    ]
    req = ChatRequest(message="latest msg", history=history_items)
    # ChatRequest validator bounds history to 10
    assert len(req.history) == 10
