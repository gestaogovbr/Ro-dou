"""FastAPI entrypoint for the standalone Ro-DOU chatbot."""

from __future__ import annotations

import logging

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from .audit import AuditLog
from .auth import build_auth_dependency
from .chat import ChatService
from .config import AppConfig, load_config
from .conversation import ConversationStore
from .models import (
    AuthenticatedUser,
    ChatRequest,
    ChatResponse,
    PublicationSearchRequest,
    SearchResult,
)
from .providers import LLMProvider, create_provider
from .search import PublicationSearchService

logging.basicConfig(level=logging.INFO)


def create_app(
    config: AppConfig | None = None,
    provider: LLMProvider | None = None,
    search_service: PublicationSearchService | None = None,
) -> FastAPI:
    settings = config or load_config()
    audit_log = AuditLog(settings.audit_log)
    publication_search = search_service or PublicationSearchService(
        settings.search,
        settings.chat.max_results,
        settings.timezone,
        audit_log=audit_log,
    )
    llm_provider = provider or create_provider(settings.chat.ai)
    conversations = ConversationStore(
        ttl_seconds=settings.chat.conversation_ttl_seconds,
        max_conversations=settings.chat.max_conversations,
    )
    chat_service = ChatService(
        config=settings.chat,
        timezone=settings.timezone,
        provider=llm_provider,
        search_service=publication_search,
        conversation_store=conversations,
    )
    authenticate = build_auth_dependency(settings.auth)

    application = FastAPI(title="Ro-DOU Chatbot API", version="1.0.0")
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Authorization", "Content-Type", "X-User-Name"],
    )

    @application.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @application.post("/api/v1/chat", response_model=ChatResponse)
    def chat(
        request: ChatRequest,
        user: AuthenticatedUser = Depends(authenticate),
    ) -> ChatResponse:
        if not settings.chat.enabled:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Chat is disabled",
            )
        response = chat_service.answer(request, user)
        audit_log.log_interaction(
            {
                "event": "chat_interaction",
                "conversation_id": response.conversation_id,
                "client_id": response.client_id,
                "user_name": user.name,
                "request": request.message,
                "answer": response.answer,
                "intent": (
                    response.intent.model_dump(mode="json")
                    if response.intent
                    else None
                ),
                "needs_clarification": response.needs_clarification,
            }
        )
        return response

    @application.post("/api/v1/publications/search", response_model=SearchResult)
    def search_publications(
        request: PublicationSearchRequest,
        user: AuthenticatedUser = Depends(authenticate),
    ) -> SearchResult:
        del user
        return publication_search.search(request.to_intent())

    application.state.config = settings
    application.state.chat_service = chat_service
    application.state.search_service = publication_search
    application.state.audit_log = audit_log
    return application


app = create_app()
