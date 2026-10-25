"""Validação dos YAMLs enviados pela tela de gestão de DAGs.

Além do schema oficial (``schemas.RoDouConfig``), aplica regras próprias da
tela, que amplia quem pode criar DAGs em relação ao fluxo via git:

- limite de tamanho e proibição de âncoras/aliases YAML (evita expansão
  exponencial na validação);
- ``dag.id`` restrito aos caracteres aceitos pelo Airflow (vira nome de arquivo);
- canais de notificação restritos a uma lista de esquemas, com o host do
  Teams verificado (evita usar o Apprise para fazer requisições a hosts
  internos);
- agenda (``schedule``) validada como expressão cron;
- levantamento das conexões e variáveis do Airflow referenciadas, para que a
  API exija permissão de leitura sobre elas.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import urlsplit

import yaml

MAX_CONTENT_BYTES = 256 * 1024
DAG_ID_RE = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_.-]{0,194}$")

# discord:// e slack:// só falam com os hosts fixos dos serviços; o host de
# workflows:// é livre no Apprise e por isso é verificado como o do https.
DEFAULT_NOTIFICATION_SCHEMES = ("discord", "slack", "workflows", "workflow")
HOST_CHECKED_SCHEMES = {"https", "workflows", "workflow"}
SCHEDULE_PRESETS = {"@once", "@continuous"}
# Webhook do Teams via Workflows (Power Automate), aceito pelo Apprise como https
TEAMS_WORKFLOW_HOST_RE = re.compile(
    r"(^|\.)(logic\.azure\.com|powerplatform\.com)$", re.IGNORECASE
)
LEGACY_WEBHOOK_HOSTS = {
    "slack": {"hooks.slack.com"},
    "discord": {"discord.com", "discordapp.com"},
}


@dataclass
class ValidationResult:
    data: Optional[dict] = None
    dag_id: Optional[str] = None
    errors: list[str] = field(default_factory=list)
    connections: set[str] = field(default_factory=set)
    variables: set[str] = field(default_factory=set)

    @property
    def valid(self) -> bool:
        return not self.errors


def allowed_notification_schemes() -> set[str]:
    raw = os.getenv("RO_DOU__DAG_MANAGER_NOTIFICATION_SCHEMES")
    if raw is None:
        return set(DEFAULT_NOTIFICATION_SCHEMES)
    return {s.strip().lower() for s in raw.split(",") if s.strip()}


def _has_alias(content: str) -> bool:
    return any(
        isinstance(event, yaml.AliasEvent) or getattr(event, "anchor", None)
        for event in yaml.parse(content, Loader=yaml.SafeLoader)
    )


def _format_pydantic_errors(exc) -> list[str]:
    messages = []
    for err in exc.errors():
        loc = ".".join(str(part) for part in err.get("loc", ()))
        msg = err.get("msg", "valor inválido")
        messages.append(f"{loc}: {msg}" if loc else msg)
    return messages


def _searches(dag: dict) -> list[dict]:
    search = dag.get("search")
    if isinstance(search, dict):
        return [search]
    if isinstance(search, list):
        return [s for s in search if isinstance(s, dict)]
    return []


def _check_notifications(report: dict, errors: list[str]) -> None:
    schemes = allowed_notification_schemes()
    for url in report.get("notification") or []:
        if not isinstance(url, str):
            continue
        parts = urlsplit(url.strip())
        scheme = parts.scheme.lower()
        teams_host = bool(parts.hostname) and bool(
            TEAMS_WORKFLOW_HOST_RE.search(parts.hostname)
        )
        if scheme in HOST_CHECKED_SCHEMES:
            if teams_host and (scheme == "https" or scheme in schemes):
                continue
            if scheme == "https" or scheme in schemes:
                errors.append(
                    f"report.notification: `{scheme}://` só é aceito para o Microsoft "
                    "Teams, com host em logic.azure.com ou powerplatform.com."
                )
                continue
        elif scheme in schemes:
            continue
        permitidos = ", ".join(sorted(f"{s}://" for s in schemes))
        errors.append(
            "report.notification: canal não permitido pela tela "
            f"(`{scheme or url[:20]}`). Use {permitidos} ou um webhook do Teams "
            "(Workflows). Outros canais do Apprise devem ser configurados via git."
        )
    for channel, hosts in LEGACY_WEBHOOK_HOSTS.items():
        conf = report.get(channel)
        if not isinstance(conf, dict) or not conf.get("webhook"):
            continue
        host = (urlsplit(str(conf["webhook"])).hostname or "").lower()
        if host not in hosts or not str(conf["webhook"]).startswith("https://"):
            errors.append(
                f"report.{channel}.webhook: o endereço deve ser https em "
                f"{' ou '.join(sorted(hosts))}."
            )


def _check_schedule(dag: dict, errors: list[str]) -> None:
    schedule = dag.get("schedule")
    if schedule is None or schedule in SCHEDULE_PRESETS:
        return
    from croniter import croniter

    if not isinstance(schedule, str) or not croniter.is_valid(schedule):
        errors.append(
            "dag.schedule: expressão cron inválida (ex.: `0 8 * * MON-FRI` ou `@daily`)."
        )


def secret_values(data) -> list[str]:
    """URLs de webhook (com token) presentes na configuração."""
    dag = data.get("dag") if isinstance(data, dict) else None
    report = dag.get("report") if isinstance(dag, dict) else None
    if not isinstance(report, dict):
        return []
    values = [u for u in report.get("notification") or [] if isinstance(u, str)]
    for channel in LEGACY_WEBHOOK_HOSTS:
        conf = report.get(channel)
        if isinstance(conf, dict) and isinstance(conf.get("webhook"), str):
            values.append(conf["webhook"])
    return [v for v in values if v.strip()]


def mask_secret(value: str) -> str:
    parts = urlsplit(value.strip())
    if parts.scheme and parts.hostname:
        return f"{parts.scheme}://{parts.hostname}/***"
    return "***"


def mask_secrets(content: str, data):
    """Oculta os tokens dos webhooks no YAML e nos dados já carregados."""
    for value in sorted(set(secret_values(data)), key=len, reverse=True):
        content = content.replace(value, mask_secret(value))
    dag = data.get("dag") if isinstance(data, dict) else None
    report = dag.get("report") if isinstance(dag, dict) else None
    if isinstance(report, dict):
        if isinstance(report.get("notification"), list):
            report["notification"] = [
                mask_secret(u) if isinstance(u, str) else u for u in report["notification"]
            ]
        for channel in LEGACY_WEBHOOK_HOSTS:
            conf = report.get(channel)
            if isinstance(conf, dict) and isinstance(conf.get("webhook"), str):
                conf["webhook"] = mask_secret(conf["webhook"])
    return content, data


def _collect_references(dag: dict, result: ValidationResult) -> None:
    for search in _searches(dag):
        terms = search.get("terms")
        if not isinstance(terms, dict):
            continue
        if terms.get("from_airflow_variable"):
            result.variables.add(str(terms["from_airflow_variable"]))
        db_select = terms.get("from_db_select")
        if isinstance(db_select, dict) and db_select.get("conn_id"):
            result.connections.add(str(db_select["conn_id"]))
    ai_config = dag.get("ai_config")
    if isinstance(ai_config, dict) and ai_config.get("api_key_var"):
        result.variables.add(str(ai_config["api_key_var"]))


def validate_content(content: str) -> ValidationResult:
    """Valida o YAML de uma DAG e devolve os dados e os erros encontrados."""
    result = ValidationResult()
    if not isinstance(content, str) or not content.strip():
        result.errors.append("O conteúdo do YAML está vazio.")
        return result
    if len(content.encode("utf-8")) > MAX_CONTENT_BYTES:
        result.errors.append(
            f"O YAML excede o limite de {MAX_CONTENT_BYTES // 1024} KB."
        )
        return result

    try:
        if _has_alias(content):
            result.errors.append(
                "Âncoras e aliases YAML (`&` e `*`) não são aceitos pela tela."
            )
            return result
        data = yaml.safe_load(content)
    except yaml.YAMLError as exc:
        result.errors.append(f"YAML inválido: {exc}")
        return result

    if not isinstance(data, dict) or not isinstance(data.get("dag"), dict):
        result.errors.append("O YAML deve começar com a chave `dag:`.")
        return result
    result.data = data
    dag = data["dag"]

    dag_id = dag.get("id")
    if not isinstance(dag_id, str) or not DAG_ID_RE.match(dag_id):
        result.errors.append(
            "dag.id: use só letras sem acento, números, `_`, `-` ou `.` "
            "(até 195 caracteres, sem começar por `.` ou `-`)."
        )
    else:
        result.dag_id = dag_id

    # import tardio: o schema puxa os módulos do Ro-DOU para o sys.path
    from pydantic import ValidationError
    from ro_dou_src.schemas import RoDouConfig

    try:
        RoDouConfig(**data)
    except ValidationError as exc:
        result.errors.extend(_format_pydantic_errors(exc))
    except (TypeError, ValueError) as exc:
        result.errors.append(str(exc))

    _check_schedule(dag, result.errors)
    report = dag.get("report")
    if isinstance(report, dict):
        _check_notifications(report, result.errors)
    _collect_references(dag, result)
    return result
