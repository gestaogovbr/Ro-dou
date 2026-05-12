import logging
import re
from datetime import date


class OpenSearchQueryBuilder:
    """Builds OpenSearch DSL query bodies from a structured search payload.

    The payload is a dictionary that maps search fields to lists of values.
    Supported keys:

    - ``texto``: full-text search terms; supports boolean operators
      ``&`` (AND), ``!`` (AND NOT), ``|`` (OR) and grouping with ``()``.
    - ``pubdate``: one or two ISO-8601 dates (``YYYY-MM-DD``). A single date
      is treated as an exact match; two dates define a ``[from, to]`` range.
    - ``pubname``: DOU section identifiers (e.g. ``"DO1"``, ``"DO2E"``).
    - ``artcategory``: publication category filter (match-phrase).
    - ``artcategory_ignore``: categories to exclude via ``must_not``.
    - ``arttype``: article type filter (match-phrase).
    - ``identifica``, ``titulo``, ``subtitulo``, ``name``: title/name filters
      (match-phrase).
    - ``terms_ignore``: exact phrases to exclude from ``texto_plain``.

    Example usage::

        qb = QueryBuilder()
        qb.payload = {
            "texto": ["Termo 1", "Termo 2 & Termo 3"],
            "pubdate": ["2024-04-01"],
            "pubname": ["DO1"],
        }
        query_body = qb.build()
        response = client.search(body=query_body, index=INDEX_NAME)
    """

    def __init__(self):
        self.payload: dict

    def add_term(self, field, term):
        if field not in self.payload:
            self.payload[field] = []
        self.payload[field].append(term)

    def build(self) -> dict:
        return self._generate_opensearch_query()

    def _generate_opensearch_query(self) -> dict:
        """Generate an OpenSearch DSL query from a search payload dict.

        Mirrors the logic of _generate_sql but produces an OpenSearch bool query.

        Args:
            payload (dict): A dictionary containing search parameters.
                example = {
                    "texto": ["Termo 1", "Termo 2 & Termo 3"],
                    "pubdate": ["2024-04-01", "2024-04-01"],
                    "pubname": ["DO1"],
                    "artcategory_ignore": ["Ministério X/Órgão Y"],
                    "terms_ignore": ["Termo Ignorado"],
                }

        Returns:
            dict: An OpenSearch query body dict.
        """
        allowed_keys = [
            "name",
            "pubname",
            "artcategory",
            "artcategory_ignore",
            "arttype",
            "identifica",
            "titulo",
            "subtitulo",
            "texto",
            "terms_ignore",
        ]

        pub_date = self.payload.get("pubdate", [date.today().strftime("%Y-%m-%d")])
        pub_date_from = pub_date[0]
        pub_date_to = pub_date[1] if len(pub_date) > 1 else pub_date_from

        filter_clauses = [
            {"range": {"pubdate": {"gte": pub_date_from, "lte": pub_date_to}}}
        ]
        must_clauses = []
        must_not_clauses = []

        filtered_dict = {
            k: self.payload[k]
            for k in self.payload
            if k in allowed_keys and self.payload[k]
        }

        for key, values in filtered_dict.items():
            if key == "texto":
                if any(values):
                    qs_clauses = []
                    for term in values:
                        if not term or not term.strip():
                            continue
                        qs = self._term_to_opensearch_qs(term)
                        if qs.strip():
                            qs_clauses.append(
                                {
                                    "query_string": {
                                        "query": qs,
                                        "default_field": "texto_plain",
                                    }
                                }
                            )
                    if len(qs_clauses) == 1:
                        must_clauses.append(qs_clauses[0])
                    elif len(qs_clauses) > 1:
                        must_clauses.append(
                            {"bool": {"should": qs_clauses, "minimum_should_match": 1}}
                        )

            elif key == "artcategory_ignore":
                must_not_clauses.extend(
                    {"match_phrase_prefix": {"artcategory": value}}
                    for value in values
                    if value
                )

            elif key == "terms_ignore":
                must_not_clauses.extend(
                    {
                        "query_string": {
                            "query": f'"{value}"',
                            "default_field": "texto_plain",
                        }
                    }
                    for value in values
                    if value
                )

            else:
                should_clauses = [
                    {"match_phrase": {key: value}} for value in values if value
                ]
                if len(should_clauses) == 1:
                    must_clauses.append(should_clauses[0])
                elif len(should_clauses) > 1:
                    must_clauses.append(
                        {"bool": {"should": should_clauses, "minimum_should_match": 1}}
                    )

        bool_query: dict = {"filter": filter_clauses}
        if must_clauses:
            bool_query["must"] = must_clauses
        if must_not_clauses:
            bool_query["must_not"] = must_not_clauses

        logging.info("Generated OpenSearch Query:")
        logging.info(bool_query)

        return {"query": {"bool": bool_query}, "size": 10000}

    def _term_to_opensearch_qs(self, term: str) -> str:
        """Convert a term expression (possibly with operators &, !, |, (, )) to
        OpenSearch query_string syntax.

        Operator mapping:
            & → AND
            ! → AND NOT
            | → OR
            (, ) → preserved as grouping

        Args:
            term (str): A search term expression, e.g. "term1 & term2 ! term3".

        Returns:
            str: An OpenSearch query_string expression, e.g. '"term1" AND "term2" AND NOT "term3"'.
        """
        operator_chars = "&!|()"
        sub_terms = re.split(rf"\s*([{re.escape(operator_chars)}])\s*", term)
        sub_terms = [t for t in sub_terms if t.strip()]

        parts = []
        for sub_term in sub_terms:
            if sub_term == "!":
                parts.append("AND NOT")
            elif sub_term == "&":
                parts.append("AND")
            elif sub_term == "|":
                parts.append("OR")
            elif sub_term in ("(", ")"):
                parts.append(sub_term)
            else:
                escaped = sub_term.replace("\\", "\\\\").replace('"', '\\"')
                parts.append(f'"{escaped}"')

        return " ".join(parts)
