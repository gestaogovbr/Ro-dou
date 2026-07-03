import logging
import re
from datetime import date

from .config import NEURAL_SEARCH_MIN_SCORE  # type: ignore
from .embeddings import embed_query  # type: ignore


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

    def build(self) -> dict:
        return self._generate_opensearch_query()

    @classmethod
    def _redact_vectors_for_log(cls, value):
        """Replace raw embedding vectors with a short placeholder for logging.

        Embedding vectors have hundreds of floats each; logging them verbatim
        drowns out everything else in the query log line.
        """
        if isinstance(value, dict):
            return {
                key: (
                    f"<vector dim={len(val)}>"
                    if key == "vector" and isinstance(val, list)
                    else cls._redact_vectors_for_log(val)
                )
                for key, val in value.items()
            }
        if isinstance(value, list):
            return [cls._redact_vectors_for_log(item) for item in value]
        return value

    @staticmethod
    def _preprocess_texto(term: str) -> str:
        """Normalize legacy text operators to OpenSearch boolean keywords."""
        term = re.sub(r"&{1,2}", " AND ", term)
        term = re.sub(r"\|{1,2}", " OR ", term)
        term = re.sub(r"(?:(?<=\s)|(?<=\()|^)!", " NOT ", term)
        return re.sub(r"\s+", " ", term).strip()

    @staticmethod
    def build_named_match_clause(
        field: str, term: str, match_phrase: bool = False
    ) -> dict:
        """Build a match clause named with the original configured term.

        OpenSearch returns this name in ``matched_queries`` when the clause
        contributes to a hit, allowing callers to report matched terms without
        re-running local text matching.
        """
        if match_phrase or " " in term.strip():
            return {
                "match_phrase": {
                    field: {
                        "query": term,
                        "_name": term,
                    }
                }
            }

        match_params = {
            "query": term,
            "_name": term,
        }

        return {
            "match": {
                field: {
                    **match_params,
                }
            }
        }

    @classmethod
    def _tokenize_texto_expression(cls, expression: str) -> list:
        """Split a text expression into terms, operators, and parentheses."""
        expression = cls._preprocess_texto(expression)
        tokens = []
        position = 0

        def word_operator_at(index):
            """Return a boolean operator starting at ``index``, if present."""
            match = re.match(r"(AND|OR|NOT)\b", expression[index:], re.IGNORECASE)
            if not match:
                return None
            if index > 0 and (
                expression[index - 1].isalnum() or expression[index - 1] == "_"
            ):
                return None
            return match.group(1).upper()

        while position < len(expression):
            char = expression[position]
            if char.isspace():
                position += 1
                continue

            if char == '"':
                end = expression.find('"', position + 1)
                if end == -1:
                    end = len(expression)
                value = expression[position + 1 : end].strip()
                if value:
                    tokens.append(("TERM", value, True))
                position = end + 1
                continue

            if char == "(":
                tokens.append(("LPAREN", char))
                position += 1
                continue

            if char == ")":
                tokens.append(("RPAREN", char))
                position += 1
                continue

            if char in {"&", "|", "!"}:
                symbol = expression[position : position + 2]
                if symbol not in {"&&", "||"}:
                    symbol = char
                tokens.append(
                    {
                        "&": ("AND", "AND"),
                        "&&": ("AND", "AND"),
                        "|": ("OR", "OR"),
                        "||": ("OR", "OR"),
                        "!": ("NOT", "NOT"),
                    }[symbol]
                )
                position += len(symbol)
                continue

            op = word_operator_at(position)
            if op:
                tokens.append((op, op))
                position += len(op)
                continue

            start = position
            while position < len(expression):
                if expression[position] in {'"', "(", ")", "&", "|", "!"}:
                    break
                if word_operator_at(position):
                    break
                position += 1
            value = expression[start:position].strip()
            if value:
                tokens.append(("TERM", value, False))

        return tokens

    @classmethod
    def _parse_texto_expression(cls, expression: str):
        """Parse a text expression into a small boolean syntax tree.

        The parser supports quoted phrases, parentheses, and the precedence
        order ``NOT`` > ``AND`` > ``OR``.
        """
        tokens = cls._tokenize_texto_expression(expression)
        position = 0

        def peek():
            """Return the current token without consuming it."""
            return tokens[position] if position < len(tokens) else None

        def consume(expected_type=None):
            """Consume and return the current token when it matches."""
            nonlocal position
            token = peek()
            if token is None:
                return None
            if expected_type and token[0] != expected_type:
                return None
            position += 1
            return token

        def parse_primary():
            """Parse a term or parenthesized expression."""
            token = peek()
            if token is None:
                return None
            if token[0] == "TERM":
                consume("TERM")
                return ("TERM", token[1], token[2])
            if token[0] == "LPAREN":
                consume("LPAREN")
                node = parse_or()
                consume("RPAREN")
                return node
            return None

        def parse_not():
            """Parse unary NOT expressions."""
            if peek() and peek()[0] == "NOT":
                consume("NOT")
                node = parse_not()
                return ("NOT", node) if node else None
            return parse_primary()

        def parse_and():
            """Parse AND expressions, including implicit adjacent ANDs."""
            node = parse_not()
            while peek() and peek()[0] in {"AND", "NOT", "LPAREN", "TERM"}:
                if peek()[0] == "AND":
                    consume("AND")
                right = parse_not()
                if not right:
                    break
                node = ("AND", node, right)
            return node

        def parse_or():
            """Parse OR expressions at the lowest precedence level."""
            node = parse_and()
            while peek() and peek()[0] == "OR":
                consume("OR")
                right = parse_and()
                if not right:
                    break
                node = ("OR", node, right)
            return node

        return parse_or()

    @classmethod
    def _texto_node_to_clause(cls, node, field: str = "texto_plain") -> dict:
        """Convert a parsed boolean node into OpenSearch DSL clauses."""
        if not node:
            return {}

        node_type = node[0]
        if node_type == "TERM":
            return cls.build_named_match_clause(field, node[1], match_phrase=node[2])

        if node_type == "NOT":
            clause = cls._texto_node_to_clause(node[1], field)
            return {"bool": {"must_not": [clause]}} if clause else {}

        if node_type == "AND":
            bool_clause = {"must": [], "must_not": []}
            for child in node[1:]:
                child_clause = cls._texto_node_to_clause(child, field)
                if not child_clause:
                    continue
                child_bool = child_clause.get("bool", {})
                if set(child_bool.keys()) == {"must_not"}:
                    bool_clause["must_not"].extend(child_bool["must_not"])
                else:
                    bool_clause["must"].append(child_clause)

            return {"bool": {key: value for key, value in bool_clause.items() if value}}

        if node_type == "OR":
            should = []
            for child in node[1:]:
                child_clause = cls._texto_node_to_clause(child, field)
                if child_clause:
                    should.append(child_clause)
            return {"bool": {"should": should, "minimum_should_match": 1}}

        return {}

    @classmethod
    def build_texto_clause(cls, expression: str) -> dict:
        """Build a named OpenSearch clause for one configured text expression."""
        node = cls._parse_texto_expression(expression)
        return cls._texto_node_to_clause(node)

    @classmethod
    def _extract_plain_terms(cls, expression: str) -> str:
        """Strip boolean operators/parentheses from a texto expression.

        Returns the configured search terms as plain natural-language text,
        suitable for embedding (e.g. ``"Ministério & Saúde"`` -> ``"Ministério
        Saúde"``).
        """
        tokens = cls._tokenize_texto_expression(expression)
        return " ".join(token[1] for token in tokens if token[0] == "TERM").strip()

    @classmethod
    def build_semantic_clause(
        cls, expression: str, min_score: float = NEURAL_SEARCH_MIN_SCORE
    ) -> dict:
        """Build a k-NN clause finding documents semantically close to ``expression``.

        Returns an empty dict when the expression has no plain terms to embed
        or when the embedding model is unavailable, so callers can fall back
        to keyword-only matching instead of failing the whole search.

        Deliberately omits ``filter`` here: combining it with radial search's
        ``min_score`` triggers an upstream OpenSearch k-NN bug ("[knn]
        requires exactly one of k, distance or score to be set") even though
        it's documented as supported for the lucene engine
        (https://github.com/opensearch-project/k-NN/issues/2836, still open
        as of OpenSearch 2.19). Correctness isn't affected: the outer bool
        query's ``filter``/``must`` clauses already restrict the final result
        set regardless of which ``should`` clause matched.
        """
        plain_text = cls._extract_plain_terms(expression)
        if not plain_text:
            return {}
        logging.info(
            "Neural search: embedding query text=%r (min_score=%s)",
            plain_text,
            min_score,
        )
        try:
            vector = embed_query(plain_text)
        except Exception:
            logging.warning(
                "Failed to compute query embedding for semantic search, "
                "falling back to keyword-only matching.",
                exc_info=True,
            )
            return {}

        return {
            "knn": {
                "embedding": {
                    "vector": vector,
                    "min_score": min_score,
                }
            }
        }

    def _generate_opensearch_query(self) -> dict:
        """Build an OpenSearch bool query body from ``self.payload``.

        Returns a dict ready to be passed as the ``body`` argument to
        ``client.search()``, with ``query``, ``highlight``, ``size`` (200), and
        ``sort`` (by ``_score`` desc) keys. Text clauses are named with the
        original configured terms so OpenSearch can report them through
        ``matched_queries``.
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

        neural_search = bool(self.payload.get("neural_search", False))
        min_score = self.payload.get("min_score") or NEURAL_SEARCH_MIN_SCORE

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
        texto_values = filtered_dict.pop("texto", None)

        for key, values in filtered_dict.items():
            if key == "artcategory_ignore":
                must_not_clauses.extend(
                    {"match_phrase_prefix": {"artcategory": value}}
                    for value in values
                    if value
                )

            elif key == "terms_ignore":
                must_not_clauses.extend(
                    {"match_phrase": {"texto_plain": value}}
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

        if texto_values:
            phrase_clauses = []
            semantic_clauses = []
            for term in texto_values:
                if not term or not term.strip():
                    continue
                text_clause = self.build_texto_clause(term)
                if text_clause:
                    phrase_clauses.append(text_clause)
                if neural_search:
                    semantic_clause = self.build_semantic_clause(term, min_score)
                    if semantic_clause:
                        semantic_clauses.append(semantic_clause)

            text_result = None
            if len(phrase_clauses) == 1:
                text_result = phrase_clauses[0]
            elif len(phrase_clauses) > 1:
                text_result = {
                    "bool": {"should": phrase_clauses, "minimum_should_match": 1}
                }

            semantic_result = None
            if len(semantic_clauses) == 1:
                semantic_result = semantic_clauses[0]
            elif len(semantic_clauses) > 1:
                semantic_result = {
                    "dis_max": {"queries": semantic_clauses, "tie_breaker": 0.0}
                }

            if text_result and semantic_result:
                clause = {
                    "bool": {
                        "should": [text_result, semantic_result],
                        "minimum_should_match": 1,
                    }
                }
            else:
                clause = text_result or semantic_result

            if clause:
                must_clauses.append(clause)

        bool_query: dict = {"filter": filter_clauses}
        if must_clauses:
            bool_query["must"] = must_clauses
        if must_not_clauses:
            bool_query["must_not"] = must_not_clauses

        logging.info("Generated OpenSearch Query:")
        logging.info(self._redact_vectors_for_log(bool_query))

        return {
            "query": {"bool": bool_query},
            "highlight": {
                "pre_tags": ["<%%>"],
                "post_tags": ["</%%>"],
                "fields": {
                    "texto_plain": {},
                },
            },
            "size": 200,
            "sort": [{"_score": "desc"}],
        }
