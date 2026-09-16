"""Conversation orchestration independent of HTTP and search infrastructure."""

from __future__ import annotations

import logging
import re
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from datetime import datetime
from threading import BoundedSemaphore
from typing import Any
from uuid import uuid4
from zoneinfo import ZoneInfo

from .config import ChatConfig
from .conversation import (
    ConversationAccessError,
    ConversationNotFoundError,
    ConversationStore,
)
from .dates import resolve_relative_dates
from .models import AuthenticatedUser, ChatRequest, ChatResponse, SearchIntent, SearchResult
from .providers import IntentProviderError, LLMProvider
from .search import NO_PUBLICATIONS_TODAY_MESSAGE, PublicationSearchService

logger = logging.getLogger("rodou_chatbot")


class ChatService:
    def __init__(
        self,
        config: ChatConfig,
        timezone: str,
        provider: LLMProvider,
        search_service: PublicationSearchService,
        conversation_store: ConversationStore,
    ) -> None:
        self._config = config
        self._timezone = timezone
        self._provider = provider
        self._search_service = search_service
        self._conversations = conversation_store
        self._provider_executor = ThreadPoolExecutor(
            max_workers=config.max_concurrent_ai_calls,
            thread_name_prefix="intent-provider",
        )
        self._provider_slots = BoundedSemaphore(config.max_concurrent_ai_calls)

    def answer(self, request: ChatRequest, user: AuthenticatedUser) -> ChatResponse:
        client_id = request.client_id or uuid4()
        owner_id = (
            f"user:{user.name}:client:{client_id}"
            if user.name
            else f"client:{client_id}"
        )
        try:
            state = self._conversations.get_or_create(request.conversation_id, owner_id)
        except (ConversationAccessError, ConversationNotFoundError):
            state = self._conversations.get_or_create(None, owner_id)
            return ChatResponse(
                conversation_id=state.conversation_id,
                client_id=client_id,
                answer=(
                    "A conversa informada não existe ou pertence a outro usuário. "
                    "Iniciei uma nova conversa."
                ),
                needs_clarification=True,
            )
        if re.search(r"\bmeu\s+nome\b", request.message, re.IGNORECASE) and not user.name:
            return ChatResponse(
                conversation_id=state.conversation_id,
                client_id=client_id,
                answer=(
                    "Para pesquisar por “meu nome”, informe seu nome no perfil "
                    "ou no campo de identificação do chatbot."
                ),
                needs_clarification=True,
            )

        today = datetime.now(ZoneInfo(self._timezone)).date()
        provider_context: dict[str, Any] = {
            "today": today.isoformat(),
            "user_name": user.name,
            "previous_intent": (
                state.last_intent.model_dump(mode="json") if state.last_intent else None
            ),
        }
        interpretation_started = time.perf_counter()
        try:
            intent = self._interpret_with_timeout(request.message, provider_context)
        except (IntentProviderError, FutureTimeoutError) as exc:
            logger.warning(
                "chat_intent_failed provider=%s model=%s error=%s",
                self._provider.name,
                self._provider.model,
                type(exc).__name__,
            )
            return ChatResponse(
                conversation_id=state.conversation_id,
                client_id=client_id,
                answer=(
                    "Não consegui interpretar a consulta com segurança. "
                    "Informe o assunto, órgão e período de forma mais específica."
                ),
                needs_clarification=True,
            )
        interpretation_ms = (time.perf_counter() - interpretation_started) * 1000

        if state.last_intent and intent.context_action == "refine":
            intent = self._merge_previous_intent(state.last_intent, intent)
        requested_dates = resolve_relative_dates(request.message, today)
        if requested_dates:
            intent = intent.model_copy(
                update={
                    "date_from": requested_dates[0],
                    "date_to": requested_dates[1],
                }
            )
        if user.name and re.search(r"\bmeu\s+nome\b", request.message, re.IGNORECASE):
            intent = intent.model_copy(update={"terms": [user.name]})
        # Organizations already have their own safe artcategory filter. Keeping
        # field=artcategory here would incorrectly search topical terms such as
        # "dengue" inside the organization name.
        if intent.organizations and intent.field == "artcategory":
            intent = intent.model_copy(update={"field": None})
        intent = SearchIntent.model_validate(
            {**intent.model_dump(), "limit": min(intent.limit, self._config.max_results)}
        )

        if not self._has_useful_filter(intent):
            return ChatResponse(
                conversation_id=state.conversation_id,
                client_id=client_id,
                answer=(
                    "Não consegui identificar um termo, órgão ou período seguro "
                    "para a busca. Você pode detalhar a consulta?"
                ),
                intent=intent,
                needs_clarification=True,
            )

        # Ro-DOU's conversational search is intentionally restricted to the
        # current publication date. User/provider dates are never allowed to
        # widen or move this boundary to previous days.
        intent = intent.model_copy(update={"date_from": today, "date_to": today})

        search_started = time.perf_counter()
        try:
            result = self._search_service.search(intent)
        except Exception as exc:
            logger.warning(
                "chat_search_failed source=publication_search error=%s",
                type(exc).__name__,
            )
            return ChatResponse(
                conversation_id=state.conversation_id,
                client_id=client_id,
                answer=(
                    "A fonte de publicações não respondeu dentro do esperado. "
                    "Tente novamente em instantes."
                ),
                intent=intent,
                needs_clarification=True,
            )
        search_ms = (time.perf_counter() - search_started) * 1000
        self._conversations.save(
            state,
            intent,
            [publication.id for publication in result.results],
        )
        logger.info(
            "chat_completed provider=%s model=%s intent=%s interpretation_ms=%.2f "
            "search_ms=%.2f result_count=%d",
            self._provider.name,
            self._provider.model,
            intent.intent,
            interpretation_ms,
            search_ms,
            result.total,
        )
        return ChatResponse(
            conversation_id=state.conversation_id,
            client_id=client_id,
            answer=self._format_answer(result),
            intent=intent,
            search_result=result,
        )

    def _interpret_with_timeout(
        self,
        message: str,
        context: dict[str, Any],
    ) -> SearchIntent:
        if not self._provider_slots.acquire(blocking=False):
            raise IntentProviderError("Intent provider is busy")
        try:
            future = self._provider_executor.submit(
                self._provider.parse_search_intent,
                message,
                context,
            )
        except Exception:
            self._provider_slots.release()
            raise
        future.add_done_callback(lambda completed: self._provider_slots.release())
        try:
            return future.result(timeout=self._config.ai.timeout)
        except FutureTimeoutError:
            future.cancel()
            raise

    @staticmethod
    def _merge_previous_intent(
        previous: SearchIntent,
        current: SearchIntent,
    ) -> SearchIntent:
        values = current.model_dump()
        clear_filters = set(current.clear_filters)
        for field_name in (
            "terms",
            "excluded_terms",
            "organizations",
            "sections",
        ):
            if not values[field_name] and field_name not in clear_filters:
                values[field_name] = getattr(previous, field_name)
        if values["field"] is None and "field" not in clear_filters:
            values["field"] = previous.field
        if "exact_search" not in current.model_fields_set:
            values["exact_search"] = previous.exact_search
        if values["date_from"] is None and "dates" not in clear_filters:
            values["date_from"] = previous.date_from
        if values["date_to"] is None and "dates" not in clear_filters:
            values["date_to"] = previous.date_to
        if "limit" not in current.model_fields_set:
            values["limit"] = previous.limit
        values["context_action"] = "replace"
        values["clear_filters"] = []
        return SearchIntent.model_validate(values)

    @staticmethod
    def _has_useful_filter(intent: SearchIntent) -> bool:
        return bool(
            intent.terms
            or intent.organizations
            or intent.sections
            or intent.date_from
            or intent.date_to
        )

    @staticmethod
    def _format_answer(result: SearchResult) -> str:
        if not result.results:
            return result.message or NO_PUBLICATIONS_TODAY_MESSAGE
        lines = [f"Encontrei {result.total} publicação(ões).", ""]
        for index, publication in enumerate(result.results, start=1):
            title = publication.title or "Publicação sem título"
            if publication.url:
                title = f"[{title}]({publication.url})"
            details = [
                value
                for value in (
                    f"Órgão: {publication.organization}"
                    if publication.organization
                    else None,
                    f"Seção: {publication.section}" if publication.section else None,
                    (
                        f"Data: {publication.publication_date.strftime('%d/%m/%Y')}"
                        if publication.publication_date
                        else None
                    ),
                )
                if value
            ]
            lines.append(f"{index}. {title}")
            if details:
                lines.append(f"   {' • '.join(details)}")
            content_label = (
                "Ementa" if publication.content_type == "ementa" else "Recorte"
            )
            content = publication.content or "Conteúdo não disponível."
            lines.append(f"   {content_label}: {content}")
            lines.append("")
        return "\n".join(lines)
