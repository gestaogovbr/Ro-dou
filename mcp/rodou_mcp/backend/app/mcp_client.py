"""Thin wrapper around the official MCP Python client."""

from __future__ import annotations

import json
from typing import Any

from fastapi import HTTPException
from mcp import ClientSession
from mcp.client.sse import sse_client


class MCPClient:
    """Call Ro-DOU MCP tools from FastAPI request handlers."""

    def __init__(self, server_url: str) -> None:
        self._server_url = server_url

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Call a tool and return its structured result."""
        async with sse_client(self._server_url) as streams:
            async with ClientSession(*streams) as session:
                await session.initialize()
                result = await session.call_tool(name, arguments=arguments)

        is_error = getattr(result, "is_error", False) or getattr(result, "isError", False)
        if is_error:
            message = self._first_text_content(result) or "MCP tool call failed"
            raise HTTPException(status_code=502, detail=message)

        structured = getattr(result, "structured_content", None) or getattr(
            result,
            "structuredContent",
            None,
        )
        if structured:
            return dict(structured)
        text = self._first_text_content(result)
        if text:
            try:
                parsed = json.loads(text)
            except json.JSONDecodeError:
                return {"answer": text, "sources": []}
            if isinstance(parsed, dict):
                return parsed
            return {"answer": str(parsed), "sources": []}
        return {}

    @staticmethod
    def _first_text_content(result: Any) -> str | None:
        """Return the first textual MCP content block, when present."""
        if not result.content:
            return None
        text = getattr(result.content[0], "text", None)
        if not text:
            return None
        return str(text)
