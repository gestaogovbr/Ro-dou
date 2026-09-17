from __future__ import annotations

import stat
from concurrent.futures import ThreadPoolExecutor
from datetime import date

from fastapi.testclient import TestClient

from rodou_chatbot.app import create_app
from rodou_chatbot.audit import AuditLog
from rodou_chatbot.config import (
    AIConfig,
    AppConfig,
    AuditLogConfig,
    ChatConfig,
    SearchConfig,
)
from rodou_chatbot.models import PublicationResult, SearchIntent, SearchResult
from rodou_chatbot.search import PublicationSearchService


class FakeProvider:
    name = "fake"
    model = "fake"

    def parse_search_intent(self, message: str, context: dict) -> SearchIntent:
        return SearchIntent(terms=["dengue"])


class FakeSearch:
    def search(self, intent: SearchIntent) -> SearchResult:
        return SearchResult(
            total=1,
            results=[PublicationResult(id="1", title="Portaria")],
        )


def test_chat_interaction_is_written_without_credentials(tmp_path) -> None:
    config = AppConfig(
        chat=ChatConfig(ai=AIConfig()),
        audit_log=AuditLogConfig(directory=str(tmp_path)),
    )
    app = create_app(
        config=config,
        provider=FakeProvider(),
        search_service=FakeSearch(),  # type: ignore[arg-type]
    )

    response = TestClient(app).post(
        "/api/v1/chat",
        json={"message": "publicações sobre dengue"},
    )

    assert response.status_code == 200
    content = (tmp_path / "chat-history.txt").read_text(encoding="utf-8")
    assert '"event":"chat_interaction"' in content
    assert '"request":"publicações sobre dengue"' in content
    assert '"answer":"Encontrei 1 publicação(ões).' in content
    assert "api_token" not in content
    assert "postgres_dsn" not in content


def test_parameterized_sql_is_written_to_separate_text_file(tmp_path) -> None:
    audit = AuditLog(AuditLogConfig(directory=str(tmp_path)))
    service = PublicationSearchService(
        SearchConfig(),
        max_results=20,
        audit_log=audit,
    )

    class FakeCursor:
        def __init__(self) -> None:
            self.executed = []

        def execute(self, statement, parameters) -> None:
            self.executed.append((statement, parameters))

    cursor = FakeCursor()
    statement = "SELECT * FROM dou_inlabs.article_raw WHERE pubdate = %(date)s"
    parameters = {"date": date(2026, 9, 16), "term": "dengue"}

    service._execute_sql(cursor, "search_publications", statement, parameters)

    assert cursor.executed == [(statement, parameters)]
    content = (tmp_path / "sql-queries.txt").read_text(encoding="utf-8")
    assert '"event":"sql_query"' in content
    assert '"operation":"search_publications"' in content
    assert "SELECT * FROM dou_inlabs.article_raw" in content
    assert '"term":"dengue"' in content
    assert "postgresql://" not in content


def test_audit_files_are_private_and_handlers_are_reused(tmp_path) -> None:
    config = AuditLogConfig(directory=str(tmp_path))
    first = AuditLog(config)
    second = AuditLog(config)

    first.log_interaction({"event": "first"})
    second.log_interaction({"event": "second"})

    path = tmp_path / "chat-history.txt"
    assert stat.S_IMODE(tmp_path.stat().st_mode) == 0o700
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert len(first._interaction_logger.handlers) == 1  # type: ignore[union-attr]
    assert first._interaction_logger is second._interaction_logger


def test_audit_rotation_and_concurrent_writes(tmp_path) -> None:
    audit = AuditLog(
        AuditLogConfig(
            directory=str(tmp_path),
            max_bytes=10_000,
            backup_count=2,
        )
    )

    with ThreadPoolExecutor(max_workers=4) as executor:
        list(
            executor.map(
                lambda index: audit.log_interaction(
                    {"event": "concurrent", "index": index, "content": "x" * 300}
                ),
                range(50),
            )
        )

    files = list(tmp_path.glob("chat-history.txt*"))
    assert len(files) >= 2
    assert all(stat.S_IMODE(path.stat().st_mode) == 0o600 for path in files)
    assert sum(
        path.read_text(encoding="utf-8").count('"event":"concurrent"')
        for path in files
    ) == 50


def test_disabled_audit_does_not_create_files(tmp_path) -> None:
    audit = AuditLog(
        AuditLogConfig(enabled=False, directory=str(tmp_path / "disabled"))
    )

    audit.log_interaction({"event": "ignored"})
    audit.log_sql("ignored", "SELECT 1", {})

    assert not (tmp_path / "disabled").exists()
