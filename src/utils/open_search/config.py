"""Configuration for OpenSearch connection and index settings.
This module loads airflow/environment variables for OpenSearch connection
parameters and defines constants for index names and other settings.
"""

import os
from airflow.models import Variable

# Try to load OpenSearch connection parameters from Airflow Variables, falling
# back to environment variables if not set in Airflow.
OPENSEARCH_HOST = Variable.get(
    "OPENSEARCH_HOST",
    default_var=os.getenv("OPENSEARCH_HOST", "http://localhost:9200"),
)

OPENSEARCH_USER = Variable.get(
    "OPENSEARCH_USER",
    default_var=os.getenv("OPENSEARCH_USER"),
)

OPENSEARCH_PASS = Variable.get(
    "OPENSEARCH_PASS",
    default_var=os.getenv("OPENSEARCH_PASS"),
)
OPENSEARCH_SSL = Variable.get(
    "OPENSEARCH_SSL",
    default_var=os.getenv("OPENSEARCH_SSL", False),
)
OPENSEARCH_VERIFY_CERTS = Variable.get(
    "OPENSEARCH_VERIFY_CERTS",
    default_var=os.getenv("OPENSEARCH_VERIFY_CERTS", False),
)

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
    "settings": {
        "analysis": {
            "filter": {
                "autocomplete_filter": {
                    "type": "edge_ngram",
                    "min_gram": 2,
                    "max_gram": 15,
                }
            },
            "analyzer": {
                "autocomplete": {
                    "type": "custom",
                    "tokenizer": "standard",
                    "filter": ["lowercase", "asciifolding", "autocomplete_filter"],
                }
            },
        }
    },
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
            "artcategory": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
            "artsize": {"type": "integer"},
            "artnotes": {"type": "text"},
            "numberpage": {"type": "integer"},
            "pdfpage": {"type": "keyword"},
            "editionnumber": {"type": "text"},
            "highlighttype": {"type": "keyword"},
            "highlightpriority": {"type": "integer"},
            "highlight": {"type": "text"},
            "highlightimage": {"type": "binary", "index": False},
            "idmateria": {"type": "keyword"},
            "midias": {"type": "text"},
            "identifica": {"type": "text"},
            "data": {"type": "text"},
            "titulo": {"type": "text"},
            "subtitulo": {"type": "text"},
            "ementa": {"type": "text"},
            "texto": {"type": "text", "index": False},
            "texto_plain": {
                "type": "text",
                "analyzer": "portuguese",
                "fields": {
                    "autocomplete": {
                        "type": "text",
                        "analyzer": "autocomplete",
                        "search_analyzer": "portuguese",
                    }
                },
            },
            "assina": {"type": "text"},
            "embedding": {"type": "knn_vector", "dimension": 384},
        },
    },
}
