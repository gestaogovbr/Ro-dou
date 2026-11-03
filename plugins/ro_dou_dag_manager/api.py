"""API e páginas da tela de gestão de DAGs do Ro-DOU.

Montada pelo plugin no api-server do Airflow. A autenticação reaproveita o
login do Airflow (cookie ``_token`` ou ``Authorization: Bearer``) e as
permissões do auth manager configurado:

- listar/visualizar: leitura da DAG do arquivo (arquivos sem ``dag.id``
  válido, só com edição global de DAGs); os tokens dos webhooks ficam ocultos
  para quem não pode editar a DAG;
- criar/alterar/excluir: edição global de DAGs e da DAG afetada; se o YAML
  usar ``from_db_select``, edição da conexão; se usar
  ``from_airflow_variable`` ou ``ai_config.api_key_var``, leitura da variável.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field

from ro_dou_dag_manager.storage import DagConfStore, StoreError
from ro_dou_dag_manager.validation import (
    MAX_CONTENT_BYTES,
    mask_secrets,
    validate_content,
)

log = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).parent / "static"
# O formulário é o mesmo gerador publicado na documentação (fonte única em
# docs/docs/gerador_yaml.html), copiado para a imagem pelo Dockerfile.
DEFAULT_GERADOR_HTML = "/opt/airflow/ro_dou_docs/gerador_yaml.html"
# Exigido em toda requisição que altera dados: um formulário de outro site não
# consegue enviá-lo sem passar pelo preflight de CORS (defesa contra CSRF).
CSRF_HEADER = "X-Ro-Dou-Request"
CSP = (
    "default-src 'self'; script-src 'self' 'unsafe-inline'; "
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
    "font-src 'self' https://fonts.gstatic.com; img-src 'self' data:; "
    "connect-src 'self'; frame-ancestors 'self'; base-uri 'none'; form-action 'none'"
)


class AirflowAuthorizer:
    """Consulta o auth manager do Airflow. Substituível nos testes."""

    async def user(self, request: Request):
        from airflow.api_fastapi.core_api.security import bearer_scheme, get_user

        credentials = await bearer_scheme(request)
        return await get_user(request, oauth_token=None, bearer_credentials=credentials)

    @staticmethod
    def _manager():
        from airflow.api_fastapi.app import get_auth_manager

        return get_auth_manager()

    def can_read(self, user, dag_id: Optional[str] = None) -> bool:
        """Sem dag_id, o FAB libera quem lê ao menos uma DAG (listagem)."""
        from airflow.api_fastapi.auth.managers.models.resource_details import DagDetails

        details = DagDetails(id=dag_id) if dag_id else None
        return self._manager().is_authorized_dag(method="GET", user=user, details=details)

    def can_write(self, user, dag_id: Optional[str] = None) -> bool:
        from airflow.api_fastapi.auth.managers.models.resource_details import DagDetails

        return self._manager().is_authorized_dag(
            method="PUT", user=user, details=DagDetails(id=dag_id)
        )

    def can_use_connection(self, user, conn_id: str) -> bool:
        """from_db_select executa SQL com a conexão: exige poder editá-la."""
        from airflow.api_fastapi.auth.managers.models.resource_details import (
            ConnectionDetails,
        )

        return self._manager().is_authorized_connection(
            method="PUT", user=user, details=ConnectionDetails(conn_id=conn_id)
        )

    def can_read_variable(self, user, key: str) -> bool:
        from airflow.api_fastapi.auth.managers.models.resource_details import (
            VariableDetails,
        )

        return self._manager().is_authorized_variable(
            method="GET", user=user, details=VariableDetails(key=key)
        )

    @staticmethod
    def user_name(user) -> str:
        for attr in ("get_name", "get_id"):
            with_attr = getattr(user, attr, None)
            if callable(with_attr):
                try:
                    return str(with_attr())
                except Exception:  # pylint: disable=broad-except
                    continue
        return "desconhecido"


def get_authorizer() -> AirflowAuthorizer:
    return AirflowAuthorizer()


def get_store() -> DagConfStore:
    try:
        return DagConfStore.from_env()
    except StoreError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


class Context:
    def __init__(self, user, authorizer: AirflowAuthorizer, store: DagConfStore):
        self.user = user
        self.authorizer = authorizer
        self.store = store

    @property
    def user_name(self) -> str:
        return self.authorizer.user_name(self.user)

    def can_see(self, dag_id: Optional[str]) -> bool:
        if dag_id:
            return self.authorizer.can_read(self.user, dag_id)
        # arquivo inválido: não há DAG para checar, exige edição global
        return self.authorizer.can_write(self.user)

    def can_edit(self, editable: bool, dag_id: Optional[str]) -> bool:
        return (
            editable
            and not self.store.misconfigured
            and self.authorizer.can_write(self.user)
            and (not dag_id or self.authorizer.can_write(self.user, dag_id))
        )


async def reader(
    request: Request,
    authorizer: AirflowAuthorizer = Depends(get_authorizer),
    store: DagConfStore = Depends(get_store),
) -> Context:
    user = await authorizer.user(request)
    if not authorizer.can_read(user):
        raise HTTPException(status_code=403, detail="Sem permissão para ver DAGs.")
    return Context(user, authorizer, store)


async def writer(request: Request, ctx: Context = Depends(reader)) -> Context:
    if request.headers.get(CSRF_HEADER) != "1":
        raise HTTPException(status_code=403, detail=f"Cabeçalho {CSRF_HEADER} ausente.")
    if not ctx.authorizer.can_write(ctx.user):
        raise HTTPException(status_code=403, detail="Sem permissão para editar DAGs.")
    return ctx


class ContentBody(BaseModel):
    content: str = Field(max_length=MAX_CONTENT_BYTES)


class UpdateBody(ContentBody):
    etag: str = Field(min_length=64, max_length=64)


def _store_error(exc: StoreError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail=str(exc))


def _validate_for_write(ctx: Context, content: str):
    result = validate_content(content)
    if result.valid:
        for conn_id in sorted(result.connections):
            if not ctx.authorizer.can_use_connection(ctx.user, conn_id):
                result.errors.append(
                    f"Sem permissão para usar a conexão `{conn_id}` em from_db_select "
                    "(é preciso poder editá-la)."
                )
        for key in sorted(result.variables):
            if not ctx.authorizer.can_read_variable(ctx.user, key):
                result.errors.append(f"Sem permissão para usar a variável `{key}`.")
        if result.dag_id and not ctx.authorizer.can_write(ctx.user, result.dag_id):
            result.errors.append(f"Sem permissão para editar a DAG `{result.dag_id}`.")
    if not result.valid:
        raise HTTPException(
            status_code=422,
            detail={"message": "A configuração tem erros.", "errors": result.errors},
        )
    return result


def _audit(ctx: Context, action: str, path: str, dag_id: Optional[str]) -> None:
    log.info(
        "ro-dou dag manager: usuario=%s acao=%s arquivo=%s dag_id=%s",
        ctx.user_name,
        action,
        path,
        dag_id,
    )


def _html(path: Path) -> FileResponse:
    return FileResponse(
        path,
        media_type="text/html; charset=utf-8",
        headers={
            "Content-Security-Policy": CSP,
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "no-cache",
        },
    )


def _svg(name: str) -> FileResponse:
    # ícone do menu: público, como os demais recursos estáticos do Airflow
    return FileResponse(
        STATIC_DIR / name,
        media_type="image/svg+xml",
        headers={"X-Content-Type-Options": "nosniff", "Cache-Control": "max-age=86400"},
    )


def create_app() -> FastAPI:
    app = FastAPI(
        title="Ro-DOU — gestão de DAGs",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )

    @app.get("/", include_in_schema=False)
    def index():
        return _html(STATIC_DIR / "index.html")

    @app.get("/icon.svg", include_in_schema=False)
    def icon():
        return _svg("icon.svg")

    @app.get("/icon-dark.svg", include_in_schema=False)
    def icon_dark():
        return _svg("icon-dark.svg")

    @app.get("/gerador", include_in_schema=False)
    def gerador():
        path = Path(os.getenv("RO_DOU__GERADOR_HTML", DEFAULT_GERADOR_HTML))
        if not path.is_file():
            raise HTTPException(status_code=404, detail="Gerador de YAML não instalado.")
        return _html(path)

    @app.get("/api/status")
    def status(ctx: Context = Depends(reader)):
        managed = ctx.store.managed_source
        return {
            "user": ctx.user_name,
            "can_write": ctx.authorizer.can_write(ctx.user)
            and not ctx.store.misconfigured,
            "misconfigured": ctx.store.misconfigured,
            "managed_source": managed.index if managed else None,
            "sources": [
                {"index": s.index, "root": str(s.root), "editable": s.editable}
                for s in ctx.store.sources
            ],
        }

    @app.get("/api/dags")
    def list_dags(ctx: Context = Depends(reader)):
        items = []
        for entry in ctx.store.list_entries():
            if not ctx.can_see(entry.dag_id):
                continue
            item = entry.as_dict()
            item["can_edit"] = ctx.can_edit(entry.editable, entry.dag_id)
            items.append(item)
        return {"items": items}

    @app.get("/api/dags/{source}/{path:path}")
    def get_dag(source: int, path: str, ctx: Context = Depends(reader)):
        try:
            conf_source, content, etag = ctx.store.read(source, path)
        except StoreError as exc:
            raise _store_error(exc) from exc
        result = validate_content(content)
        if not ctx.can_see(result.dag_id):
            raise HTTPException(status_code=404, detail="Arquivo de configuração inexistente.")
        can_edit = ctx.can_edit(conf_source.editable, result.dag_id)
        data = result.data
        if not ctx.authorizer.can_write(ctx.user, result.dag_id):
            content, data = mask_secrets(content, data)
        return {
            "source": source,
            "path": path,
            "editable": conf_source.editable,
            "can_edit": can_edit,
            "content": content,
            "etag": etag,
            "dag_id": result.dag_id,
            "data": data,
            "errors": result.errors,
        }

    @app.post("/api/validate")
    def validate(body: ContentBody, ctx: Context = Depends(reader)):
        result = validate_content(body.content)
        return {
            "valid": result.valid,
            "dag_id": result.dag_id,
            "errors": result.errors,
            "data": result.data,
        }

    @app.post("/api/dags", status_code=201)
    def create_dag(body: ContentBody, ctx: Context = Depends(writer)):
        result = _validate_for_write(ctx, body.content)
        try:
            entry = ctx.store.create(result.dag_id, body.content)
        except StoreError as exc:
            raise _store_error(exc) from exc
        _audit(ctx, "criar", entry.path, entry.dag_id)
        return entry.as_dict()

    @app.put("/api/dags/{source}/{path:path}")
    def update_dag(
        source: int, path: str, body: UpdateBody, ctx: Context = Depends(writer)
    ):
        result = _validate_for_write(ctx, body.content)
        try:
            _, current, _ = ctx.store.read(source, path)
            old_id = validate_content(current).dag_id
            if old_id and old_id != result.dag_id and not ctx.authorizer.can_write(
                ctx.user, old_id
            ):
                raise HTTPException(status_code=403, detail="Sem permissão para editar esta DAG.")
            etag = ctx.store.update(source, path, result.dag_id, body.content, body.etag)
        except StoreError as exc:
            raise _store_error(exc) from exc
        _audit(ctx, "alterar", path, result.dag_id)
        return {"source": source, "path": path, "etag": etag, "dag_id": result.dag_id}

    @app.delete("/api/dags/{source}/{path:path}", status_code=204)
    def delete_dag(source: int, path: str, etag: str, ctx: Context = Depends(writer)):
        try:
            _, current, _ = ctx.store.read(source, path)
            dag_id = validate_content(current).dag_id
            if dag_id and not ctx.authorizer.can_write(ctx.user, dag_id):
                raise HTTPException(status_code=403, detail="Sem permissão para excluir esta DAG.")
            ctx.store.delete(source, path, etag)
        except StoreError as exc:
            raise _store_error(exc) from exc
        _audit(ctx, "excluir", path, dag_id)
        return Response(status_code=204)

    return app
