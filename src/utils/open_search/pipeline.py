from .client_open_search import OpenSearchClient
from .config import INDEX_NAME


class OpenSearchPipeline:
    """Handles document indexing operations against an OpenSearch cluster."""

    def __init__(self):
        # Initialize the OpenSearch client once and reuse across calls
        self.client = OpenSearchClient().get_client()

    def send(self, doc, pipeline=None):
        """Index a document into OpenSearch.

        Args:
            doc: Dictionary containing the document to index. Must include
                 an 'id' field used as the document ID.
            pipeline: Optional name of an ingest pipeline to run on the document.

        Returns:
            The OpenSearch index response.
        """
        params = {}
        if pipeline:
            # Attach the ingest pipeline name to the request params
            params["pipeline"] = pipeline
        response = self.client.index(
            index=INDEX_NAME,
            id=doc.get("id"),
            body=doc,
            params=params,
        )

        return response
