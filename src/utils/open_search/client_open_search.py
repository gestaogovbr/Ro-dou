"""Utility module for managing OpenSearch client connections.
This module provides a wrapper class for creating and managing connections"""

from opensearchpy import OpenSearch  # type: ignore
from .config import OPENSEARCH_HOST, OPENSEARCH_USER, OPENSEARCH_PASS, \
    OPENSEARCH_SSL, OPENSEARCH_VERIFY_CERTS  # type: ignore


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
            use_ssl=OPENSEARCH_SSL,
            verify_certs=OPENSEARCH_VERIFY_CERTS,
        )

    def get_client(self) -> OpenSearch:
        """Return the underlying OpenSearch client instance."""
        return self._client
