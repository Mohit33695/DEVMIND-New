"""
Codebase Chat Service.

Purpose:
Orchestrates grounded repository chat by integrating repository validation,
index status checking, RAG retrieval, context formatting, and LLM completions.
"""

import os
from typing import List, Optional
from app.schemas.chat import ChatMessage, ChatRequest, ChatResponse
from app.services.context import ContextBuilder
from app.services.llm import LLMProvider, MockLLMProvider
from app.services.rag import CodebaseRAGService
from app.services.storage import RepositoryNotFoundError, RepositoryStorageService


class CodebaseChatService:
    """Service managing grounded codebase conversational chat queries."""

    _llm_provider: Optional[LLMProvider] = None

    @classmethod
    def get_llm_provider(cls) -> LLMProvider:
        """Returns the active LLM provider instance (defaults to MockLLMProvider)."""
        if cls._llm_provider is None:
            cls._llm_provider = MockLLMProvider()
        return cls._llm_provider

    @classmethod
    def set_llm_provider(cls, provider: LLMProvider) -> None:
        """Allows overriding LLM provider for testing or custom configurations."""
        cls._llm_provider = provider

    @classmethod
    def chat_with_repository(
        cls,
        repo_id: str,
        request: ChatRequest,
    ) -> ChatResponse:
        """
        Executes grounded repository chat query.

        Args:
            repo_id: Unique repository identifier.
            request: ChatRequest containing message query and history.

        Returns:
            ChatResponse: Answer synthesis with source references.

        Raises:
            RepositoryNotFoundError: If repo_id does not exist in storage.
            ValueError: If index status is invalid, message is empty, or query fails.
        """
        if not repo_id or not repo_id.strip():
            raise RepositoryNotFoundError("Invalid or missing repository ID.")

        repo_dir = RepositoryStorageService.get_repository_directory(repo_id)
        if not os.path.exists(repo_dir) or not os.path.isdir(repo_dir):
            raise RepositoryNotFoundError(f"Repository with ID '{repo_id}' not found.")

        # 1. Inspect RAG Index Status
        index_status = CodebaseRAGService.get_index_status(repo_id)

        if index_status.status == "not_indexed":
            raise ValueError("Repository is not indexed. Please index the repository first.")
        elif index_status.status == "indexing":
            raise ValueError("Repository indexing is in progress.")
        elif index_status.status == "failed":
            raise ValueError(f"Repository indexing failed: {index_status.error or 'Unknown error'}")

        # 2. Retrieve relevant RAG vector chunks
        retrieval_resp = CodebaseRAGService.retrieve_codebase_context(
            repo_id=repo_id,
            query=request.message,
            top_k=request.top_k,
            score_threshold=request.score_threshold or 0.0,
        )

        # 3. Format context blocks and source references
        context_str, sources = ContextBuilder.format_untrusted_context(
            results=retrieval_resp.results,
            top_k=request.top_k,
        )

        # 4. Filter history to ensure role restriction (user/assistant only, max 6 items)
        filtered_history: List[ChatMessage] = []
        for msg in (request.history or [])[-6:]:
            if msg.role in ("user", "assistant"):
                filtered_history.append(msg)

        # 5. Generate LLM Response
        system_instruction = ContextBuilder.construct_system_prompt()
        provider = cls.get_llm_provider()

        llm_response = provider.generate_response(
            system_instruction=system_instruction,
            user_message=request.message,
            grounded_context=context_str,
            history=filtered_history,
        )

        return ChatResponse(
            repo_id=repo_id,
            query=request.message,
            answer=llm_response.answer,
            sources=sources,
            provider=llm_response.provider_name,
            retrieved_count=len(sources),
            grounded=llm_response.grounded,
            indexed_status=index_status.status,
        )
