"""Configuration for OpenSearch connection and index settings.
This module loads environment variables for OpenSearch connection parameters and defines constants for index names and other settings.
"""

import os

OPENSEARCH_HOST = os.getenv("OPENSEARCH_HOST", "http://localhost:9200")
OPENSEARCH_USER = os.getenv("OPENSEARCH_USER", None)
OPENSEARCH_PASS = os.getenv("OPENSEARCH_PASS", None)

if not OPENSEARCH_HOST:
    raise EnvironmentError("Environment variable OPENSEARCH_HOST not found!")

INDEX_NAME = "dou"
