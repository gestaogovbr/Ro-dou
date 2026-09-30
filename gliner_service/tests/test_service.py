"""Unit tests for the GLiNER2 service (no torch or network required)."""

import os
import sys

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app import create_app, max_body_bytes  # noqa: E402
from extractor import (  # noqa: E402
    GlinerExtractor,
    GlinerSettings,
    load_settings,
    normalize_entities,
)


class FakeSchema:
    def __init__(self):
        self.entity_spec = None

    def entities(self, spec):
        self.entity_spec = spec
        return self


class FakeModel:
    """Mimics ``batch_extract_long`` returning one result per input text."""

    def __init__(self, results=None):
        self.results = results
        self.calls = []

    def create_schema(self):
        return FakeSchema()

    def batch_extract_long(self, texts, schema, **kwargs):
        self.calls.append({"texts": list(texts), "schema": schema, **kwargs})
        if self.results is not None:
            return self.results[: len(texts)]
        return [
            {"entities": {"person": [{"text": t.split()[0], "confidence": 0.9}]}}
            for t in texts
        ]


def make_settings(**overrides):
    data = {"entities": {"person": "Pessoa física.", "process": "Processo."}}
    data.update(overrides)
    return GlinerSettings(**data)


# Settings ------------------------------------------------------------------


def test_default_config_file_is_valid():
    settings = load_settings()
    assert settings.model == "fastino/gliner2.5-multi-v1"
    assert "person" in settings.entity_names
    assert "official_publication" in settings.entity_names


@pytest.mark.parametrize("name", ["Person", "1st", "a-b", "entities.x", ""])
def test_invalid_entity_names_are_rejected(name):
    with pytest.raises(ValidationError):
        make_settings(entities={name: "desc"})


def test_empty_entity_description_is_rejected():
    with pytest.raises(ValidationError):
        make_settings(entities={"person": "  "})


def test_overlap_must_be_smaller_than_chunk_size():
    with pytest.raises(ValidationError):
        make_settings(chunk_size=64, chunk_overlap=64)


def test_unknown_setting_is_rejected():
    with pytest.raises(ValidationError):
        make_settings(unknown_option=1)


def test_fingerprint_ignores_throughput_settings():
    base = make_settings()
    assert base.fingerprint() == make_settings(batch_size=2).fingerprint()
    assert base.fingerprint() == make_settings(max_texts_per_request=4).fingerprint()
    assert base.fingerprint() != make_settings(threshold=0.9).fingerprint()
    assert (
        base.fingerprint()
        != make_settings(entities={"person": "Outra descrição."}).fingerprint()
    )


# Normalization ---------------------------------------------------------------


def test_normalize_dedupes_ignoring_case_and_whitespace():
    raw = {
        "entities": {
            "person": [
                {"text": "JOÃO  DA SILVA", "confidence": 0.99},
                {"text": "joão da silva", "confidence": 0.98},
                {"text": " Maria Souza ", "confidence": 0.97},
            ]
        }
    }
    assert normalize_entities(raw, ["person"]) == {
        "person": ["JOÃO DA SILVA", "Maria Souza"]
    }


def test_normalize_filters_confidence_and_unknown_types():
    raw = {
        "entities": {
            "person": [
                {"text": "Baixa", "confidence": 0.2},
                {"text": "Alta", "confidence": 0.8},
            ],
            "not_configured": ["X"],
        }
    }
    assert normalize_entities(raw, ["person"], min_confidence=0.5) == {
        "person": ["Alta"]
    }


def test_normalize_accepts_strings_and_bare_mapping_and_caps_values():
    raw = {"process": ["A", "B", "C", 3, None, ""]}
    assert normalize_entities(raw, ["process"], max_per_type=2) == {
        "process": ["A", "B"]
    }


@pytest.mark.parametrize("raw", [None, [], "x", {"entities": []}])
def test_normalize_handles_malformed_results(raw):
    assert normalize_entities(raw, ["person"]) == {}


# Extractor -----------------------------------------------------------------


def test_extractor_skips_empty_texts_and_keeps_order():
    model = FakeModel()
    extractor = GlinerExtractor(make_settings(), model=model)

    results = extractor.extract(["Ana foi nomeada", "", "   ", "Bruno exonerado"])

    assert results == [{"person": ["Ana"]}, {}, {}, {"person": ["Bruno"]}]
    assert model.calls[0]["texts"] == ["Ana foi nomeada", "Bruno exonerado"]


def test_extractor_passes_settings_and_truncates_text():
    model = FakeModel()
    settings = make_settings(
        max_text_chars=5, chunk_size=100, chunk_overlap=10, threshold=0.3
    )
    extractor = GlinerExtractor(settings, model=model)

    extractor.extract(["abcdefghij"])

    call = model.calls[0]
    assert call["texts"] == ["abcde"]
    assert call["chunk_size"] == 100
    assert call["chunk_overlap"] == 10
    assert call["threshold"] == 0.3
    assert call["include_confidence"] is True
    assert call["schema"].entity_spec == settings.entities


def test_extractor_does_not_call_model_without_text():
    model = FakeModel()
    extractor = GlinerExtractor(make_settings(), model=model)
    assert extractor.extract([]) == []
    assert extractor.extract(["", None]) == [{}, {}]
    assert model.calls == []


# HTTP API --------------------------------------------------------------------


@pytest.fixture
def client(monkeypatch):
    monkeypatch.delenv("GLINER_API_TOKEN", raising=False)
    extractor = GlinerExtractor(make_settings(max_texts_per_request=2), FakeModel())
    with TestClient(create_app(extractor)) as test_client:
        yield test_client


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_info_exposes_fingerprint_and_entities(client):
    body = client.get("/info").json()
    assert body["entities"] == ["person", "process"]
    assert body["fingerprint"] == make_settings().fingerprint()
    assert body["max_texts_per_request"] == 2


def test_extract_returns_results_in_order(client):
    response = client.post("/extract", json={"texts": ["Ana x", "Bia y"]})
    assert response.status_code == 200
    body = response.json()
    assert body["results"] == [{"person": ["Ana"]}, {"person": ["Bia"]}]
    assert body["fingerprint"] == make_settings().fingerprint()


def test_extract_rejects_too_many_texts(client):
    response = client.post("/extract", json={"texts": ["a", "b", "c"]})
    assert response.status_code == 413


def test_extract_rejects_invalid_payload(client):
    assert client.post("/extract", json={"texts": "a"}).status_code == 422


def test_token_is_required_when_configured(monkeypatch):
    monkeypatch.setenv("GLINER_API_TOKEN", "segredo-de-teste")
    extractor = GlinerExtractor(make_settings(), FakeModel())
    with TestClient(create_app(extractor)) as test_client:
        assert test_client.get("/health").status_code == 200
        assert test_client.get("/info").status_code == 401
        assert (
            test_client.get(
                "/info", headers={"Authorization": "Bearer errado"}
            ).status_code
            == 401
        )
        assert (
            test_client.post(
                "/extract",
                json={"texts": ["a"]},
                headers={"Authorization": "Bearer segredo-de-teste"},
            ).status_code
            == 200
        )


# Limits and hardening ---------------------------------------------------------


def test_chars_per_request_must_cover_one_full_text():
    with pytest.raises(ValidationError):
        make_settings(max_text_chars=1000, max_chars_per_request=999)


def test_default_config_pins_model_revision():
    assert load_settings().revision


def test_info_exposes_size_limits(client):
    body = client.get("/info").json()
    assert body["max_text_chars"] == make_settings().max_text_chars
    assert body["max_chars_per_request"] == make_settings().max_chars_per_request


def test_extract_rejects_too_many_characters(monkeypatch):
    monkeypatch.delenv("GLINER_API_TOKEN", raising=False)
    settings = make_settings(max_text_chars=10, max_chars_per_request=15)
    with TestClient(create_app(GlinerExtractor(settings, FakeModel()))) as test_client:
        ok = test_client.post("/extract", json={"texts": ["a" * 10, "b" * 5]})
        too_big = test_client.post("/extract", json={"texts": ["a" * 10, "b" * 6]})
    assert ok.status_code == 200
    assert too_big.status_code == 413


def test_oversized_body_is_rejected_before_parsing(monkeypatch):
    monkeypatch.delenv("GLINER_API_TOKEN", raising=False)
    settings = make_settings(max_text_chars=10, max_chars_per_request=10)
    model = FakeModel()
    with TestClient(create_app(GlinerExtractor(settings, model))) as test_client:
        response = test_client.post(
            "/extract",
            content=b'{"texts": ["' + b"x" * (max_body_bytes(10) + 1) + b'"]}',
            headers={"Content-Type": "application/json"},
        )
    assert response.status_code == 413
    assert model.calls == []


def test_post_without_content_length_is_rejected(client):
    def chunks():
        yield b'{"texts": ["a"]}'

    response = client.post(
        "/extract", content=chunks(), headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 411


def test_interactive_docs_are_disabled(client):
    assert client.get("/docs").status_code == 404
    assert client.get("/openapi.json").status_code == 404
