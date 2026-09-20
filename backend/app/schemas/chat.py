"""
Repository AI Chat Data Schemas.

Purpose:
Defines Pydantic request and response models for grounded repository chat,
message history, and LLM responses with source citations.
"""

from typing import List, Optional
from pydantic import BaseModel, Field, field_validator

from app.schemas.rag import SourceReference

# Re-use SourceReference for ChatSource
ChatSource = SourceReference


class ChatMessage(BaseModel):
    """Single message in a conversation thread."""

    role: str  # Must be "user" or "assistant"
    content: str

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        clean_role = (v or "").strip().lower()
        if clean_role not in ("user", "assistant"):
            raise ValueError("ChatMessage role must be either 'user' or 'assistant'.")
        return clean_role


class ChatRequest(BaseModel):
    """Payload for initiating grounded codebase chat queries."""

    message: str
    history: List[ChatMessage] = Field(default_factory=list)
    top_k: int = Field(5, ge=1, le=10)
    score_threshold: Optional[float] = 0.0

    @field_validator("message")
    @classmethod
    def validate_message(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Chat message cannot be empty or whitespace.")
        if len(v) > 1000:
            raise ValueError("Chat message cannot exceed 1000 characters.")
        return v

    @field_validator("history")
    @classmethod
    def validate_history_roles(cls, v: List[ChatMessage]) -> List[ChatMessage]:
        for item in v:
            if item.role not in ("user", "assistant"):
                raise ValueError("History contains invalid role. Only 'user' and 'assistant' are allowed.")
        return v[:10]  # Bound history length to recent 10 messages


# Alias for backward compatibility
RepositoryChatRequest = ChatRequest


class ChatResponse(BaseModel):
    """Grounded AI response containing synthesized answer and source citations."""

    answer: str
    sources: List[SourceReference] = Field(default_factory=list)
    retrieved_count: int = 0
    grounded: bool = True
    repo_id: Optional[str] = None
    query: Optional[str] = None
    provider: Optional[str] = "MockLLMProvider (Development/Test Mode)"
    indexed_status: Optional[str] = "indexed"


# Alias for backward compatibility
RepositoryChatResponse = ChatResponse
