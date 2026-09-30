"""Named entity extraction for DOU publications using GLiNER2.

``gliner2``/``torch`` are imported lazily, so settings and result
normalization can be tested without the ML stack installed.
"""

import hashlib
import json
import os
import re
from typing import Any, Dict, List, Optional, Sequence

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

DEFAULT_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.yaml")

# Entity names become OpenSearch field names (``entities.<name>``).
_ENTITY_NAME_RE = re.compile(r"^[a-z][a-z0-9_]{0,63}$")


class GlinerSettings(BaseModel):
    """Validated GLiNER2 extraction settings loaded from YAML."""

    model_config = ConfigDict(extra="forbid", protected_namespaces=())

    model: str = "fastino/gliner2.5-multi-v1"
    revision: Optional[str] = None
    threshold: float = Field(0.45, ge=0.0, le=1.0)
    min_confidence: float = Field(0.0, ge=0.0, le=1.0)
    chunk_size: int = Field(384, gt=0)
    chunk_overlap: int = Field(64, ge=0)
    batch_size: int = Field(8, gt=0)
    max_text_chars: int = Field(100_000, gt=0)
    max_entities_per_type: int = Field(200, gt=0)
    max_texts_per_request: int = Field(32, gt=0)
    max_chars_per_request: int = Field(100_000, gt=0)
    entities: Dict[str, str]

    @field_validator("entities")
    @classmethod
    def _validate_entities(cls, value: Dict[str, str]) -> Dict[str, str]:
        if not value:
            raise ValueError("at least one entity must be configured")
        for name, description in value.items():
            if not _ENTITY_NAME_RE.match(name):
                raise ValueError(
                    f"invalid entity name {name!r}: use lowercase letters, "
                    "digits and '_' (max. 64 characters)"
                )
            if not isinstance(description, str) or not description.strip():
                raise ValueError(f"entity {name!r} needs a description")
        return value

    @model_validator(mode="after")
    def _validate_chunking(self) -> "GlinerSettings":
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("chunk_overlap must be smaller than chunk_size")
        if self.max_chars_per_request < self.max_text_chars:
            raise ValueError("max_chars_per_request must be >= max_text_chars")
        return self

    @property
    def entity_names(self) -> List[str]:
        return list(self.entities)

    def fingerprint(self) -> str:
        """Return a hash of every setting that changes extraction output.

        Clients store it with each enriched document and reprocess documents
        whose fingerprint differs. Throughput settings are left out on purpose.
        """
        relevant = self.model_dump(
            include={
                "model",
                "revision",
                "threshold",
                "min_confidence",
                "chunk_size",
                "chunk_overlap",
                "max_text_chars",
                "max_entities_per_type",
                "entities",
            }
        )
        payload = json.dumps(relevant, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def load_settings(path: Optional[str] = None) -> GlinerSettings:
    """Load and validate GLiNER2 settings from a YAML file."""
    path = path or DEFAULT_CONFIG_PATH
    with open(path, "r", encoding="utf-8") as file:
        data = yaml.safe_load(file) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Invalid GLiNER2 configuration in {path}: expected a mapping.")
    return GlinerSettings(**data)


def _normalize_key(value: str) -> str:
    return " ".join(value.split()).casefold()


def normalize_entities(
    raw_result: Any,
    entity_names: Sequence[str],
    min_confidence: float = 0.0,
    max_per_type: int = 200,
) -> Dict[str, List[str]]:
    """Convert a GLiNER2 result into ``{entity_type: [distinct values]}``.

    Accepts both ``{"entities": {...}}`` and a bare entity mapping, with items
    as plain strings or dicts carrying ``text`` and ``confidence``. Values are
    deduplicated ignoring case and extra whitespace, keeping the first
    spelling found. Unknown entity types are dropped.
    """
    if not isinstance(raw_result, dict):
        return {}
    source = raw_result.get("entities", raw_result)
    if not isinstance(source, dict):
        return {}

    entities: Dict[str, List[str]] = {}
    for entity_type in entity_names:
        values = source.get(entity_type) or []
        if not isinstance(values, list):
            continue
        extracted: List[str] = []
        seen = set()
        for item in values:
            confidence = None
            if isinstance(item, dict):
                text = item.get("text")
                confidence = item.get("confidence")
            else:
                text = item
            if not isinstance(text, str):
                continue
            text = " ".join(text.split())
            if not text:
                continue
            if confidence is not None and float(confidence) < min_confidence:
                continue
            key = _normalize_key(text)
            if key in seen:
                continue
            seen.add(key)
            extracted.append(text)
            if len(extracted) >= max_per_type:
                break
        if extracted:
            entities[entity_type] = extracted
    return entities


class GlinerExtractor:
    """Loads a GLiNER2 model once and extracts entities from batches of text."""

    def __init__(self, settings: GlinerSettings, model: Any = None):
        """Args:
        settings: Validated extraction settings.
        model: Preloaded model, mainly for tests. When omitted, the model is
            loaded from ``settings.model``.
        """
        self.settings = settings
        self.model = model if model is not None else self._load_model(settings)
        self.schema = self.model.create_schema()
        self.schema.entities(dict(settings.entities))

    @staticmethod
    def _load_model(settings: GlinerSettings) -> Any:
        # AutoExtractor honours the architecture saved in the checkpoint;
        # GLiNER2.from_pretrained forces the span head and fails to load
        # gliner2.5 checkpoints.
        from gliner2 import AutoExtractor  # type: ignore

        kwargs = {}
        if settings.revision and not os.path.isdir(settings.model):
            kwargs["revision"] = settings.revision
        model = AutoExtractor.from_pretrained(settings.model, **kwargs)
        model.eval()
        return model

    def extract(self, texts: Sequence[str]) -> List[Dict[str, List[str]]]:
        """Return normalized entities for each text, preserving order."""
        if not texts:
            return []
        limit = self.settings.max_text_chars
        prepared = [(text or "")[:limit] for text in texts]
        # Empty texts are skipped so they do not reach the model.
        indexes = [i for i, text in enumerate(prepared) if text.strip()]
        results: List[Dict[str, List[str]]] = [{} for _ in prepared]
        if not indexes:
            return results

        raw_results = self.model.batch_extract_long(
            [prepared[i] for i in indexes],
            self.schema,
            batch_size=self.settings.batch_size,
            threshold=self.settings.threshold,
            include_confidence=True,
            chunk_size=self.settings.chunk_size,
            chunk_overlap=self.settings.chunk_overlap,
        )
        for index, raw in zip(indexes, raw_results):
            results[index] = normalize_entities(
                raw,
                self.settings.entity_names,
                min_confidence=self.settings.min_confidence,
                max_per_type=self.settings.max_entities_per_type,
            )
        return results
