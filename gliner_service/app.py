"""HTTP service that extracts named entities from DOU publications.

Endpoints:

- ``GET /health``: liveness/readiness probe.
- ``GET /info``: model, configuration fingerprint and entity names.
- ``POST /extract``: ``{"texts": [...]}`` -> ``{"fingerprint", "results"}``,
  one ``{entity_type: [values]}`` mapping per text, in the same order.

Environment variables:

- ``GLINER_CONFIG_PATH``: YAML settings file (defaults to ``config.yaml``).
- ``GLINER_API_TOKEN``: when set, requests to ``/info`` and ``/extract`` must
  send ``Authorization: Bearer <token>``.

Interactive docs (``/docs``, ``/openapi.json``) are disabled.
"""

import hmac
import logging
import os
import threading
from contextlib import asynccontextmanager
from typing import Dict, List, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from extractor import GlinerExtractor, load_settings

logger = logging.getLogger("gliner_service")


class ExtractRequest(BaseModel):
    texts: List[str]


class ExtractResponse(BaseModel):
    fingerprint: str
    results: List[Dict[str, List[str]]]


class InfoResponse(BaseModel):
    model: str
    revision: Optional[str]
    fingerprint: str
    entities: List[str]
    max_texts_per_request: int
    max_text_chars: int
    max_chars_per_request: int


def max_body_bytes(max_chars: int) -> int:
    """Upper bound for an /extract body: JSON may escape each character as
    ``\\uXXXX`` (6 bytes), plus room for the envelope."""
    return max_chars * 6 + 64 * 1024


def create_app(extractor: Optional[GlinerExtractor] = None) -> FastAPI:
    """Build the FastAPI app.

    Args:
        extractor: Ready extractor, mainly for tests. When omitted, settings
            and model are loaded once at startup.
    """
    state = {"extractor": extractor}
    # The model is not safe for concurrent use and inference is CPU bound, so
    # requests are served one at a time.
    inference_lock = threading.Lock()
    api_token = os.getenv("GLINER_API_TOKEN") or None

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        if state["extractor"] is None:
            settings = load_settings(os.getenv("GLINER_CONFIG_PATH") or None)
            logger.info(
                "Loading model %s (fingerprint %s)",
                settings.model,
                settings.fingerprint(),
            )
            state["extractor"] = GlinerExtractor(settings)
        yield

    app = FastAPI(
        title="Ro-DOU GLiNER2",
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )

    @app.middleware("http")
    async def limit_body_size(request: Request, call_next):
        # Reject oversized bodies before they are read and parsed.
        if request.method == "POST":
            length = request.headers.get("content-length")
            if length is None or not length.isdigit():
                return JSONResponse(
                    status_code=411, content={"detail": "Content-Length required"}
                )
            limit = max_body_bytes(state["extractor"].settings.max_chars_per_request)
            if int(length) > limit:
                return JSONResponse(
                    status_code=413, content={"detail": "Request body too large"}
                )
        return await call_next(request)

    def require_token(authorization: Optional[str] = Header(default=None)) -> None:
        if api_token is None:
            return
        expected = f"Bearer {api_token}"
        if not authorization or not hmac.compare_digest(
            authorization.encode("utf-8"), expected.encode("utf-8")
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
            )

    @app.get("/health")
    def health() -> Dict[str, str]:
        return {"status": "ok"}

    @app.get("/info", response_model=InfoResponse, dependencies=[Depends(require_token)])
    def info() -> InfoResponse:
        settings = state["extractor"].settings
        return InfoResponse(
            model=settings.model,
            revision=settings.revision,
            fingerprint=settings.fingerprint(),
            entities=settings.entity_names,
            max_texts_per_request=settings.max_texts_per_request,
            max_text_chars=settings.max_text_chars,
            max_chars_per_request=settings.max_chars_per_request,
        )

    @app.post(
        "/extract",
        response_model=ExtractResponse,
        dependencies=[Depends(require_token)],
    )
    def extract(request: ExtractRequest) -> ExtractResponse:
        current = state["extractor"]
        settings = current.settings
        if len(request.texts) > settings.max_texts_per_request:
            raise HTTPException(
                status_code=413,
                detail=(
                    f"At most {settings.max_texts_per_request} texts per request"
                ),
            )
        if sum(len(text) for text in request.texts) > settings.max_chars_per_request:
            raise HTTPException(
                status_code=413,
                detail=(
                    f"At most {settings.max_chars_per_request} characters per request"
                ),
            )
        with inference_lock:
            results = current.extract(request.texts)
        return ExtractResponse(fingerprint=settings.fingerprint(), results=results)

    return app


app = create_app()
