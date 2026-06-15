"""FastAPI API for the Ro-DOU chatbot frontend."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .mcp_client import MCPClient
from .models import ChatRequest, ChatResponse
from .settings import BackendSettings

settings = BackendSettings()
client = MCPClient(server_url=settings.mcp_server_url)

app = FastAPI(title="Ro-DOU Chatbot API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict[str, str]:
    """Return backend health status."""
    return {"status": "ok"}


@app.post("/api/chat")
async def chat(request: ChatRequest) -> ChatResponse:
    """Answer a chatbot message through the MCP server."""
    result = await client.call_tool(
        "answer_question",
        {
            "question": request.message,
            "date_from": request.date_from,
            "date_to": request.date_to,
            "pubname": request.pubname,
            "size": request.size,
        },
    )
    return ChatResponse(
        answer=result.get("answer", "Nao foi possivel obter uma resposta do MCP."),
        sources=result.get("sources", []),
        context_source=result.get("context_source"),
        context_id=result.get("context_id"),
        fresh_context=result.get("fresh_context"),
        context_date=result.get("context_date"),
        total_publications=result.get("total_publications"),
        loaded_publications=result.get("loaded_publications"),
        ai_used=result.get("ai_used"),
    )
