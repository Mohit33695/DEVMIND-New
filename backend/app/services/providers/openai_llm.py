"""
OpenAI LLM Provider implementation using HTTP REST completions client.
"""

from typing import List, Optional
import httpx

from app.schemas.chat import ChatMessage
from app.services.context import ContextBuilder
from app.services.llm import (
    LLMProvider,
    LLMResponse,
    LLMAuthError,
    LLMRateLimitError,
    LLMNetworkError,
    LLMTimeoutError,
    LLMResponseError,
)


class OpenAILLMProvider(LLMProvider):
    """
    Production-ready OpenAI-compatible chat completion provider using direct HTTP REST requests.
    Supports system prompt security boundaries, untrusted repository context boundaries,
    bounded history, and clean domain exception mapping.
    """

    def __init__(
        self,
        api_key: str,
        model: str,
        timeout: int = 30,
        max_tokens: int = 1024,
        base_url: str = "https://api.openai.com/v1",
        transport: Optional[httpx.BaseTransport] = None,
    ):
        if not api_key or not api_key.strip():
            raise ValueError("API key must be configured for OpenAILLMProvider.")
        self.api_key = api_key.strip()
        self.model = model.strip()
        self.timeout = timeout
        self.max_tokens = max_tokens
        self.base_url = base_url.rstrip("/")
        self.transport = transport

    def get_provider_name(self) -> str:
        return f"OpenAILLMProvider ({self.model})"

    def generate_response(
        self,
        system_instruction: str,
        user_message: str,
        grounded_context: str,
        history: List[ChatMessage] = [],
    ) -> LLMResponse:
        """
        Generates a grounded LLM completion using OpenAI Chat Completions API.
        """
        endpoint = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        # 1. System instruction message
        messages = [
            {"role": "system", "content": system_instruction or ContextBuilder.construct_system_prompt()}
        ]

        # 2. Append filtered user/assistant message history
        for msg in (history or []):
            if msg.role in ("user", "assistant"):
                messages.append({"role": msg.role, "content": msg.content})

        # 3. Final user message containing untrusted repository context boundary + query
        final_user_content = ContextBuilder.build_full_prompt(
            user_message=user_message,
            formatted_context=grounded_context,
        )
        messages.append({"role": "user", "content": final_user_content})

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.0,
            "max_tokens": self.max_tokens,
        }

        try:
            with httpx.Client(timeout=float(self.timeout), transport=self.transport) as client:
                response = client.post(endpoint, headers=headers, json=payload)
        except httpx.TimeoutException as exc:
            raise LLMTimeoutError("LLM completion request timed out.") from exc
        except httpx.RequestError as exc:
            raise LLMNetworkError("LLM provider network failure.") from exc

        if response.status_code == 401:
            raise LLMAuthError("LLM provider authentication failed (HTTP 401).")
        elif response.status_code == 429:
            raise LLMRateLimitError("LLM provider rate limit exceeded (HTTP 429).")
        elif response.status_code >= 400:
            raise LLMResponseError(f"LLM provider HTTP error ({response.status_code}).")

        try:
            res_json = response.json()
        except Exception as exc:
            raise LLMResponseError("Malformed LLM response: invalid JSON.") from exc

        if not isinstance(res_json, dict) or "choices" not in res_json or not isinstance(res_json["choices"], list):
            raise LLMResponseError("Malformed LLM response: missing choices array.")

        choices = res_json["choices"]
        if not choices:
            raise LLMResponseError("Malformed LLM response: empty choices array.")

        first_choice = choices[0]
        if not isinstance(first_choice, dict) or "message" not in first_choice or not isinstance(first_choice["message"], dict):
            raise LLMResponseError("Malformed LLM response: invalid choice message structure.")

        message_obj = first_choice["message"]
        if "content" not in message_obj:
            raise LLMResponseError("Malformed LLM response: missing message content.")

        raw_content = message_obj["content"]
        if raw_content is None or not isinstance(raw_content, str):
            raise LLMResponseError("Malformed LLM response: non-string message content.")

        clean_content = raw_content.strip()
        if not clean_content:
            clean_content = (
                "Based on the indexed repository evidence available, "
                "no additional synthesis could be generated."
            )

        return LLMResponse(
            content=clean_content,
            answer=clean_content,
            provider_name=self.get_provider_name(),
            model_name=self.model,
            grounded=True,
        )
