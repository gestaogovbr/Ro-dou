"""Shared embedding model access for indexing and semantic search.

The E5 model family expects different prefixes depending on whether the text
being encoded is a document (``"passage: "``) or a search query
(``"query: "``); using the wrong prefix degrades retrieval quality.
"""

from functools import lru_cache

from sentence_transformers import SentenceTransformer  # type: ignore

from .config import EMBED_MODEL  # type: ignore


@lru_cache(maxsize=1)
def _load_model() -> SentenceTransformer:
    """Load and cache the embedding model."""
    return SentenceTransformer(EMBED_MODEL)


def embed_passage(text: str) -> list:
    """Encode a document passage for indexing."""
    return _load_model().encode(text, prompt="passage: ").tolist()


def embed_query(text: str) -> list:
    """Encode a search query for semantic retrieval."""
    return _load_model().encode(text, prompt="query: ").tolist()


def is_passage_truncated(text: str) -> bool:
    """Return True if encoding ``text`` as a passage would silently truncate it."""
    model = _load_model()
    token_count = len(model.tokenizer("passage: " + text)["input_ids"])
    return token_count > model.max_seq_length


def max_seq_length() -> int:
    """Return the embedding model's maximum input length, in tokens."""
    return _load_model().max_seq_length


# Slack for the token-count estimate in `build_passage_text`, which counts
# the prefix and body separately (real tokenization of the joined string can
# differ by a token or two at the boundary).
_TRUNCATION_SAFETY_MARGIN = 8


def build_passage_text(summary_fields: list, body: str) -> str:
    """Build the text to embed as a passage, keeping the *tail* of ``body``.

    ``summary_fields`` (e.g. ``identifica``/``titulo``/``ementa``) are short
    and kept in full, in front. ``body`` (e.g. ``texto_plain``) is usually
    the long part; when the combined text would exceed the model's token
    limit, the tail of ``body`` is kept instead of the head. DOU/INLABS
    normative acts front-load a boilerplate legal-basis preamble
    ("Considerando que...") that repeats near-verbatim across thousands of
    documents and carries little topic-specific signal — keeping the tail
    favors the operative content that usually follows it.
    """
    summary = " ".join(field for field in summary_fields if field)
    if not body:
        return summary

    tokenizer = _load_model().tokenizer
    prefix = f"passage: {summary} " if summary else "passage: "
    prefix_token_count = len(tokenizer(prefix)["input_ids"])
    budget = max_seq_length() - prefix_token_count - _TRUNCATION_SAFETY_MARGIN
    if budget <= 0:
        return summary

    body_token_ids = tokenizer(body, add_special_tokens=False)["input_ids"]
    if len(body_token_ids) > budget:
        body = tokenizer.decode(body_token_ids[-budget:], skip_special_tokens=True)

    return f"{summary} {body}".strip() if summary else body
