"""Leitura e gravação dos arquivos YAML de configuração das DAGs.

Os diretórios lidos são os mesmos do gerador de DAGs (``RO_DOU__DAG_CONF_DIR``,
separados por ``:``). Apenas o diretório gerenciado pela tela
(``RO_DOU__DAG_MANAGER_DIR``) aceita escrita; os demais — normalmente
sincronizados via git — são somente leitura.

Este módulo não depende do Airflow para poder ser testado isoladamente.
"""

from __future__ import annotations

import contextlib
import fcntl
import hashlib
import logging
import os
import re
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator, Optional

import yaml

log = logging.getLogger(__name__)

YAML_SUFFIXES = (".yaml", ".yml")
# Nome do arquivo gravado pela tela = dag_id + ".yaml". Mesmo conjunto de
# caracteres aceito pelo Airflow em dag_id, sem permitir arquivo oculto.
MANAGED_FILENAME_RE = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_.-]{0,199}\.ya?ml$")
# Nomes auxiliares não podem conter ".yaml"/".yml": o gerador seleciona
# arquivos por substring da extensão (dou_dag_generator.generate_dags).
LOCK_FILENAME = ".ro_dou_dag_manager.lock"
TMP_PREFIX = ".ro_dou_tmp-"


def is_conf_file(filename: str) -> bool:
    """Mesmo critério do gerador (dou_dag_generator.generate_dags): substring
    da extensão, de modo que ``x.yaml.bak`` também vira DAG."""
    return any(ext in filename for ext in YAML_SUFFIXES)


def _inside(path: Path, root: Path) -> bool:
    return os.path.commonpath([path.resolve(), root]) == str(root)


class StoreError(Exception):
    """Erro de operação no repositório de configurações."""

    status_code = 400


class NotFoundError(StoreError):
    status_code = 404


class ReadOnlyError(StoreError):
    status_code = 403


class ConflictError(StoreError):
    status_code = 409


class StorageIOError(StoreError):
    status_code = 500


@dataclass(frozen=True)
class ConfigSource:
    """Um diretório de configurações lido pelo gerador de DAGs."""

    index: int
    root: Path
    editable: bool


@dataclass
class DagConfEntry:
    """Resumo de um arquivo de configuração para a listagem."""

    source: int
    path: str
    editable: bool
    dag_id: Optional[str] = None
    description: Optional[str] = None
    schedule: Optional[str] = None
    sources: list[str] = field(default_factory=list)
    error: Optional[str] = None

    def as_dict(self) -> dict:
        return {
            "source": self.source,
            "path": self.path,
            "editable": self.editable,
            "dag_id": self.dag_id,
            "description": self.description,
            "schedule": self.schedule,
            "sources": self.sources,
            "error": self.error,
        }


def etag_of(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _summarize(data) -> dict:
    """Extrai dag_id, descrição, agenda e fontes de um YAML já carregado."""
    if not isinstance(data, dict) or not isinstance(data.get("dag"), dict):
        raise ValueError("o arquivo não tem a seção `dag`")
    dag = data["dag"]
    searches = dag.get("search")
    if isinstance(searches, dict):
        searches = [searches]
    sources: list[str] = []
    for search in searches if isinstance(searches, list) else []:
        if not isinstance(search, dict):
            continue
        for src in search.get("sources") or ["DOU"]:
            if isinstance(src, str) and src not in sources:
                sources.append(src)
    return {
        "dag_id": str(dag["id"]) if dag.get("id") is not None else None,
        "description": dag.get("description"),
        "schedule": dag.get("schedule"),
        "sources": sources,
    }


class DagConfStore:
    """Acesso aos YAMLs de todas as fontes, com escrita restrita ao diretório
    gerenciado."""

    def __init__(self, conf_dirs: list[str], managed_dir: str):
        self.managed_root = Path(managed_dir).resolve()
        sources: list[ConfigSource] = []
        seen: set[Path] = set()
        for raw in conf_dirs:
            if not raw:
                continue
            root = Path(raw).resolve()
            if root in seen:
                continue
            seen.add(root)
            sources.append(
                ConfigSource(
                    index=len(sources), root=root, editable=root == self.managed_root
                )
            )
        self.sources = sources
        # Se o diretório gerenciado não estiver em RO_DOU__DAG_CONF_DIR, os
        # arquivos gravados nunca virariam DAGs: a tela avisa e bloqueia a escrita.
        self.misconfigured = not any(s.editable for s in sources)

    @classmethod
    def from_env(cls) -> "DagConfStore":
        conf_dirs = (os.getenv("RO_DOU__DAG_CONF_DIR") or "").split(":")
        managed_dir = os.getenv("RO_DOU__DAG_MANAGER_DIR") or ""
        if not managed_dir:
            raise StoreError("Variável de ambiente RO_DOU__DAG_MANAGER_DIR não definida.")
        return cls(conf_dirs, managed_dir)

    # ------------------------------------------------------------------ leitura

    @property
    def managed_source(self) -> Optional[ConfigSource]:
        return next((s for s in self.sources if s.editable), None)

    def _iter_files(self) -> Iterator[tuple[ConfigSource, Path]]:
        visited: set[Path] = set()
        # o diretório gerenciado primeiro: se estiver aninhado em outra fonte,
        # seus arquivos aparecem como editáveis e não duplicados
        ordered = sorted(self.sources, key=lambda s: not s.editable)
        for source in ordered:
            if not source.root.is_dir():
                continue
            for dirpath, dirnames, filenames in os.walk(source.root):
                dirnames.sort()
                for filename in sorted(filenames):
                    if not is_conf_file(filename):
                        continue
                    path = Path(dirpath, filename)
                    real = path.resolve()
                    # symlink para fora da fonte: não lê nem lista
                    if not _inside(path, source.root):
                        continue
                    if real in visited:
                        continue
                    visited.add(real)
                    yield source, path

    def list_entries(self) -> list[DagConfEntry]:
        entries = []
        for source, path in self._iter_files():
            entry = DagConfEntry(
                source=source.index,
                path=path.relative_to(source.root).as_posix(),
                editable=source.editable,
            )
            try:
                with open(path, "r", encoding="utf-8") as file:
                    summary = _summarize(yaml.safe_load(file))
                entry.dag_id = summary["dag_id"]
                entry.description = summary["description"]
                entry.schedule = summary["schedule"]
                entry.sources = summary["sources"]
            except (OSError, yaml.YAMLError, ValueError, KeyError, TypeError) as exc:
                entry.error = f"Arquivo inválido: {exc}"[:300]
            entries.append(entry)
        entries.sort(key=lambda e: ((e.dag_id or e.path).lower(), e.source))
        return entries

    def dag_ids(self, exclude: Optional[Path] = None) -> dict[str, str]:
        """dag_id -> caminho legível, para checar unicidade."""
        ids: dict[str, str] = {}
        exclude_real = exclude.resolve() if exclude else None
        for source, path in self._iter_files():
            if exclude_real and path.resolve() == exclude_real:
                continue
            try:
                with open(path, "r", encoding="utf-8") as file:
                    dag_id = _summarize(yaml.safe_load(file))["dag_id"]
            except (OSError, yaml.YAMLError, ValueError, KeyError, TypeError):
                continue
            if dag_id:
                ids.setdefault(dag_id, path.relative_to(source.root).as_posix())
        return ids

    def resolve(self, source_index: int, relpath: str) -> tuple[ConfigSource, Path]:
        """Localiza um arquivo garantindo que ele fique dentro da fonte."""
        if not 0 <= source_index < len(self.sources):
            raise NotFoundError("Diretório de configuração inexistente.")
        source = self.sources[source_index]
        rel = Path(relpath)
        if (
            not relpath
            or rel.is_absolute()
            or ".." in rel.parts
            or not is_conf_file(rel.name)
        ):
            raise NotFoundError("Arquivo de configuração inexistente.")
        path = source.root / rel
        if not _inside(path, source.root) or not path.resolve().is_file():
            raise NotFoundError("Arquivo de configuração inexistente.")
        return source, path

    def read(self, source_index: int, relpath: str) -> tuple[ConfigSource, str, str]:
        source, path = self.resolve(source_index, relpath)
        try:
            raw = path.read_bytes()
            return source, raw.decode("utf-8"), etag_of(raw)
        except UnicodeDecodeError as exc:
            raise StoreError("O arquivo não está em UTF-8.") from exc
        except OSError as exc:
            raise StorageIOError(f"Não foi possível ler o arquivo: {exc.strerror}") from exc

    # ------------------------------------------------------------------ escrita

    def _require_managed(self) -> ConfigSource:
        source = self.managed_source
        if source is None:
            raise StoreError(
                "O diretório RO_DOU__DAG_MANAGER_DIR não está incluído em "
                "RO_DOU__DAG_CONF_DIR; as DAGs gravadas não seriam carregadas."
            )
        try:
            source.root.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise StorageIOError(f"Não foi possível criar {source.root}: {exc.strerror}") from exc
        return source

    @contextlib.contextmanager
    def _locked(self, root: Path):
        try:
            lock = open(root / LOCK_FILENAME, "a", encoding="utf-8")
        except OSError as exc:
            raise StorageIOError(
                f"Sem permissão de escrita em {root} ({exc.strerror}). "
                "Verifique o volume da tela de gestão de DAGs."
            ) from exc
        with lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            try:
                yield
            except OSError as exc:
                raise StorageIOError(f"Erro ao gravar o arquivo: {exc.strerror}") from exc
            finally:
                fcntl.flock(lock, fcntl.LOCK_UN)

    @staticmethod
    def _write_tmp(root: Path, content: str) -> Path:
        tmp = root / f"{TMP_PREFIX}{uuid.uuid4().hex}"
        with open(tmp, "w", encoding="utf-8") as file:
            file.write(content)
            file.flush()
            os.fsync(file.fileno())
        os.chmod(tmp, 0o664)
        return tmp

    def _check_unique(self, dag_id: str, exclude: Optional[Path] = None) -> None:
        other = self.dag_ids(exclude=exclude).get(dag_id)
        if other:
            raise ConflictError(
                f"Já existe uma DAG com o id `{dag_id}` (arquivo {other})."
            )

    def create(self, dag_id: str, content: str) -> DagConfEntry:
        source = self._require_managed()
        filename = f"{dag_id}.yaml"
        if not MANAGED_FILENAME_RE.match(filename):
            raise StoreError("O id da DAG gera um nome de arquivo inválido.")
        with self._locked(source.root):
            self._check_unique(dag_id)
            target = source.root / filename
            tmp = self._write_tmp(source.root, content)
            try:
                # link() falha se o destino já existir: nunca sobrescreve
                os.link(tmp, target)
            except FileExistsError as exc:
                raise ConflictError(f"O arquivo {filename} já existe.") from exc
            finally:
                tmp.unlink(missing_ok=True)
        return DagConfEntry(source=source.index, path=filename, editable=True, dag_id=dag_id)

    def update(
        self, source_index: int, relpath: str, dag_id: str, content: str, etag: str
    ) -> str:
        source, path = self.resolve(source_index, relpath)
        if not source.editable:
            raise ReadOnlyError("Esta DAG é sincronizada via git e não pode ser alterada pela tela.")
        with self._locked(source.root):
            current = etag_of(path.read_bytes())
            if current != etag:
                raise ConflictError(
                    "O arquivo foi alterado por outra pessoa desde que você o abriu. "
                    "Recarregue a página e refaça a alteração."
                )
            self._check_unique(dag_id, exclude=path)
            tmp = self._write_tmp(source.root, content)
            os.replace(tmp, path)
        return etag_of(content.encode("utf-8"))

    def delete(self, source_index: int, relpath: str, etag: str) -> None:
        source, path = self.resolve(source_index, relpath)
        if not source.editable:
            raise ReadOnlyError("Esta DAG é sincronizada via git e não pode ser excluída pela tela.")
        with self._locked(source.root):
            if etag_of(path.read_bytes()) != etag:
                raise ConflictError(
                    "O arquivo foi alterado por outra pessoa desde que você o abriu. "
                    "Recarregue a página antes de excluir."
                )
            path.unlink()
