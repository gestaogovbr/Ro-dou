"""Hash of ``texto_plain`` shared by the indexer and the GLiNER2 enrichment.

The indexer stores it in ``TEXT_HASH_FIELD`` so consumers can detect text
changes by comparing hashes, without downloading the text itself.
"""

import hashlib
from typing import Optional

TEXT_HASH_FIELD = "texto_plain_hash"
TEXT_HASH_MAPPING = {"properties": {TEXT_HASH_FIELD: {"type": "keyword"}}}


def text_hash(text: Optional[str]) -> str:
    """Return the SHA-256 hex digest of ``text`` (``None`` counts as empty)."""
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()
