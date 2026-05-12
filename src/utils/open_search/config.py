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

COLUMNS_NAME = [
    "id",
    "name",
    "idoficio",
    "pubname",
    "arttype",
    "pubdate",
    "artclass",
    "artcategory",
    "artsize",
    "artnotes",
    "numberpage",
    "pdfpage",
    "editionnumber",
    "highlighttype",
    "highlightpriority",
    "highlight",
    "highlightimage",
    "idmateria",
    "midias",
    "identifica",
    "data",
    "ementa",
    "titulo",
    "subtitulo",
    "texto",
    "assina",
]

MAPPING = {
    "mappings": {
        "properties": {
            "id": {"type": "keyword"},
            "name": {"type": "text"},
            "idoficio": {"type": "keyword"},
            "pubname": {"type": "keyword"},
            "arttype": {"type": "keyword"},
            "pubdate": {
                "type": "date",
                "format": "yyyy-MM-dd||strict_date_optional_time",
            },
            "artclass": {"type": "keyword"},
            "artcategory": {"type": "keyword"},
            "artsize": {"type": "integer"},
            "artnotes": {"type": "text"},
            "numberpage": {"type": "integer"},
            "pdfpage": {"type": "keyword"},
            "editionnumber": {"type": "integer"},
            "highlighttype": {"type": "keyword"},
            "highlightpriority": {"type": "integer"},
            "highlight": {"type": "text"},
            "highlightimage": {"type": "keyword"},
            "idmateria": {"type": "keyword"},
            "midias": {"type": "text"},
            "identifica": {"type": "text"},
            "data": {"type": "text"},
            "titulo": {"type": "text"},
            "subtitulo": {"type": "text"},
            "ementa": {"type": "text"},
            "texto": {"type": "text", "index": False},
            "assina": {"type": "text"},
        }
    }
}
