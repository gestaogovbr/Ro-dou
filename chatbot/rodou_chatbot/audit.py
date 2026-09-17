"""Persistent text audit logs for chat interactions and generated SQL."""

from __future__ import annotations

import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

from .config import AuditLogConfig


class AuditLog:
    """Write UTF-8 JSON Lines to independently rotated text files."""

    def __init__(self, config: AuditLogConfig) -> None:
        self._interaction_logger: logging.Logger | None = None
        self._sql_logger: logging.Logger | None = None
        if not config.enabled or config.directory is None:
            return

        directory = Path(config.directory)
        directory.mkdir(parents=True, exist_ok=True)
        directory.chmod(0o700)
        logger_suffix = str(directory.resolve()).replace("/", "_")
        self._interaction_logger = self._build_logger(
            f"rodou_chatbot.audit.interactions.{logger_suffix}",
            directory / "chat-history.txt",
            config,
        )
        self._sql_logger = self._build_logger(
            f"rodou_chatbot.audit.sql.{logger_suffix}",
            directory / "sql-queries.txt",
            config,
        )

    @staticmethod
    def _build_logger(
        name: str,
        path: Path,
        config: AuditLogConfig,
    ) -> logging.Logger:
        logger = logging.getLogger(name)
        logger.setLevel(logging.INFO)
        logger.propagate = False
        target = str(path.resolve())
        for handler in logger.handlers:
            if isinstance(handler, RotatingFileHandler) and handler.baseFilename == target:
                handler.maxBytes = config.max_bytes
                handler.backupCount = config.backup_count
                path.chmod(0o600)
                return logger
        handler = _SecureRotatingFileHandler(
            path,
            maxBytes=config.max_bytes,
            backupCount=config.backup_count,
            encoding="utf-8",
        )
        handler.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
        logger.addHandler(handler)
        return logger

    @staticmethod
    def _serialize(payload: dict[str, Any]) -> str:
        return json.dumps(payload, ensure_ascii=False, default=str, separators=(",", ":"))

    def log_interaction(self, payload: dict[str, Any]) -> None:
        if self._interaction_logger:
            self._interaction_logger.info(self._serialize(payload))

    def log_sql(
        self,
        operation: str,
        statement: str,
        parameters: dict[str, Any],
    ) -> None:
        if self._sql_logger:
            self._sql_logger.info(
                self._serialize(
                    {
                        "event": "sql_query",
                        "operation": operation,
                        "statement": " ".join(statement.split()),
                        "parameters": parameters,
                    }
                )
            )


class _SecureRotatingFileHandler(RotatingFileHandler):
    """Keep current and newly rotated audit files owner-readable only."""

    def _open(self):
        stream = super()._open()
        Path(self.baseFilename).chmod(0o600)
        return stream
