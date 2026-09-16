"""Small backend-controlled conversation state store."""

from __future__ import annotations

from dataclasses import dataclass, field
from threading import Lock
from time import monotonic
from uuid import UUID, uuid4

from .models import SearchIntent


@dataclass
class ConversationState:
    conversation_id: UUID
    owner_id: str
    last_intent: SearchIntent | None = None
    last_result_ids: list[str] = field(default_factory=list)
    updated_at: float = field(default_factory=monotonic)


class ConversationStore:
    def __init__(self, ttl_seconds: int, max_conversations: int) -> None:
        self._ttl_seconds = ttl_seconds
        self._max_conversations = max_conversations
        self._states: dict[UUID, ConversationState] = {}
        self._lock = Lock()

    def get_or_create(
        self,
        conversation_id: UUID | None,
        owner_id: str,
    ) -> ConversationState:
        with self._lock:
            self._evict_expired()
            if conversation_id:
                state = self._states.get(conversation_id)
                if state is None:
                    raise ConversationNotFoundError("conversation does not exist")
                if state.owner_id != owner_id:
                    raise ConversationAccessError("conversation belongs to another owner")
                state.updated_at = monotonic()
                return state
            if len(self._states) >= self._max_conversations:
                oldest = min(self._states.values(), key=lambda item: item.updated_at)
                self._states.pop(oldest.conversation_id, None)
            state = ConversationState(conversation_id=uuid4(), owner_id=owner_id)
            self._states[state.conversation_id] = state
            return state

    def save(
        self,
        state: ConversationState,
        intent: SearchIntent,
        result_ids: list[str],
    ) -> None:
        with self._lock:
            state.last_intent = intent.model_copy(deep=True)
            state.last_result_ids = result_ids[:100]
            state.updated_at = monotonic()
            self._states[state.conversation_id] = state

    def _evict_expired(self) -> None:
        threshold = monotonic() - self._ttl_seconds
        expired = [key for key, state in self._states.items() if state.updated_at < threshold]
        for key in expired:
            self._states.pop(key, None)


class ConversationNotFoundError(LookupError):
    pass


class ConversationAccessError(PermissionError):
    pass
