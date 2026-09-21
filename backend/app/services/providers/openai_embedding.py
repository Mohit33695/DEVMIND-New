"""
OpenAI Embedding Provider implementation using HTTP client.
"""

from typing import List, Optional
import httpx

from app.services.embeddings import (
    EmbeddingProvider,
    EmbeddingAuthError,
    EmbeddingRateLimitError,
    EmbeddingNetworkError,
    EmbeddingTimeoutError,
    EmbeddingResponseError,
    EmbeddingDimensionMismatchError,
)


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """
    Production-ready OpenAI-compatible semantic embedding provider using direct HTTP REST requests.
    Supports payload batching, dimension validation, response validation, and clean domain exception mapping.
    """

    def __init__(
        self,
        api_key: str,
        model: str,
        dimension: int,
        timeout: int = 30,
        batch_size: int = 100,
        base_url: str = "https://api.openai.com/v1",
        transport: Optional[httpx.BaseTransport] = None,
    ):
        if not api_key or not api_key.strip():
            raise ValueError("API key must be configured for OpenAIEmbeddingProvider.")
        self.api_key = api_key.strip()
        self.model = model.strip()
        self.dimension = dimension
        self.timeout = timeout
        self.batch_size = batch_size
        self.base_url = base_url.rstrip("/")
        self.transport = transport

    def get_dimension(self) -> int:
        return self.dimension

    def get_provider_name(self) -> str:
        return f"OpenAIEmbeddingProvider ({self.model})"

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        Embeds a list of text strings into float vector arrays.
        Splits inputs into batches according to batch_size and validates response dimensions.
        """
        if not texts:
            return []

        endpoint = f"{self.base_url}/embeddings"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        all_embeddings: List[List[float]] = []

        # Process inputs in batches
        for i in range(0, len(texts), self.batch_size):
            batch_texts = texts[i : i + self.batch_size]

            payload = {
                "input": batch_texts,
                "model": self.model,
            }

            # If model supports explicit dimensions parameter
            if self.model.startswith("text-embedding-3"):
                payload["dimensions"] = self.dimension

            try:
                with httpx.Client(timeout=float(self.timeout), transport=self.transport) as client:
                    response = client.post(endpoint, headers=headers, json=payload)
            except httpx.TimeoutException as exc:
                raise EmbeddingTimeoutError("Embedding request timed out.") from exc
            except httpx.RequestError as exc:
                raise EmbeddingNetworkError("Embedding network failure.") from exc

            if response.status_code == 401:
                raise EmbeddingAuthError("Embedding provider authentication failed (HTTP 401).")
            elif response.status_code == 429:
                raise EmbeddingRateLimitError("Embedding provider rate limit exceeded (HTTP 429).")
            elif response.status_code >= 400:
                raise EmbeddingResponseError(f"Embedding provider HTTP error ({response.status_code}).")

            try:
                res_json = response.json()
            except Exception as exc:
                raise EmbeddingResponseError("Malformed provider response: invalid JSON.") from exc

            if not isinstance(res_json, dict) or "data" not in res_json or not isinstance(res_json["data"], list):
                raise EmbeddingResponseError("Malformed provider response: missing data array.")

            data_items = res_json["data"]
            if len(data_items) != len(batch_texts):
                raise EmbeddingResponseError(
                    f"Embedding count mismatch: expected {len(batch_texts)}, got {len(data_items)}."
                )

            # Preserve exact input ordering by sorting by 'index' field
            try:
                sorted_items = sorted(data_items, key=lambda x: x.get("index", 0))
            except Exception as exc:
                raise EmbeddingResponseError("Malformed provider response: invalid item structure.") from exc

            for item in sorted_items:
                if not isinstance(item, dict) or "embedding" not in item:
                    raise EmbeddingResponseError("Malformed provider response: item missing embedding.")

                vec = item["embedding"]
                if not isinstance(vec, list) or not vec:
                    raise EmbeddingResponseError("Malformed provider response: vector is not a non-empty list.")

                # Validate vector elements are numeric floats/ints (and not bools)
                if not all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in vec):
                    raise EmbeddingResponseError("Malformed embedding vector containing non-numeric values.")

                # Validate vector dimension matches expected configured dimension
                if len(vec) != self.dimension:
                    raise EmbeddingDimensionMismatchError(
                        f"Embedding dimension mismatch: expected {self.dimension}, got {len(vec)}."
                    )

                all_embeddings.append([float(x) for x in vec])

        return all_embeddings
