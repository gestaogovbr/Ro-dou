"""Utility module for managing OpenSearch client connections.
This module provides a wrapper class for creating and managing connections"""

from opensearchpy import OpenSearch  # type: ignore
from .config import OPENSEARCH_HOST, OPENSEARCH_USER, OPENSEARCH_PASS


class OpenSearchClient:
    """Client wrapper for OpenSearch connections."""

    def __init__(self):
        """Initialize the OpenSearch client using credentials from config."""
        auth = None
        if OPENSEARCH_USER:
            auth = (OPENSEARCH_USER, OPENSEARCH_PASS)

        self._client = OpenSearch(
            hosts=[OPENSEARCH_HOST],
            http_compress=True,
            http_auth=auth,
            use_ssl=False,
            verify_certs=False,
        )

    def get_client(self) -> OpenSearch:
        """Return the underlying OpenSearch client instance."""
        return self._client
