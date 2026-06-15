from __future__ import annotations

from rodou_mcp.server.models import Publication, PublicationContext
from rodou_mcp.server.services.ai import AIService
from rodou_mcp.server.settings import Settings


def test_ai_service_falls_back_without_provider() -> None:
    service = AIService(settings=Settings(OPENSEARCH_HOST="http://opensearch:9200"))

    answer = service.answer(
        context=PublicationContext(
            context_id="test-context",
            source="postgres",
            question="O que saiu?",
            context_date="2026-06-15",
            total_publications=1,
            publications=[
                Publication(id="abc", title="Aviso", pubdate="2026-06-15"),
            ],
        ),
    )

    assert "abc" in answer
    assert "Aviso" in answer
