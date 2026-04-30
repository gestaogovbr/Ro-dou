"""Apache Airflow Hook to execute DOU searches from INLABS source."""

import copy
import re
import logging
from datetime import datetime, timedelta, date
import unicodedata
import pandas as pd
import html2text

from airflow.hooks.base import BaseHook

# from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.models import Variable

# from typing import Optional
from schemas import AIConfig, AISearchConfig
from ai.runner import AIRunner

from ro_dou_src.utils.open_search.client_open_search import OpenSearchClient  # type: ignore
from ro_dou_src.utils.open_search.config import INDEX_NAME  # type: ignore
from opensearchpy import OpenSearch  # type: ignore

from bs4 import BeautifulSoup


class INLABSHook(BaseHook):
    """A custom Apache Airflow Hook designed for executing searches via
    the DOU Postgres Database provided by INLABS.

    Attributes:
        CONN_ID (str): DOU INLABS Database Airflow conn id.
    """

    CONN_ID = "inlabs_db"
    CLIENT = OpenSearchClient().get_client()

    def __init__(self, *args, **kwargs):
        pass

    @staticmethod
    def _filter_text_terms(text_terms) -> list:
        """
        Filter the text terms by removing words that succeed the delimitator ! and
        split words based on search term operators

        Args:
            text_terms (list): The list of text terms used in the search.

        Returns:
            list: A list of filtered text terms
        """
        search_term_operators = ["&", "!", "|", "(", ")"]

        # Remove terms that precede a '!'
        text_terms = [re.sub(r"! .*", "", term).strip() for term in text_terms]
        operator_str = "".join(search_term_operators)
        split_text_terms = [
            re.split(rf"\s*[{re.escape(operator_str)}]\s*", term) for term in text_terms
        ]
        text_terms = [item for sublist in split_text_terms for item in sublist]
        # Remove blank items
        text_terms = list(filter(lambda t: t != "", text_terms))

        return text_terms

    def search_text(
        self,
        ai_config: dict,
        ai_search_config: dict,
        search_terms: dict,
        ignore_signature_match: bool,
        full_text: bool,
        text_length: int,
        use_summary: bool,
        conn_id: str = CONN_ID,
        client: OpenSearch = CLIENT,
    ) -> dict:
        """Searches the DOU Database with the provided search terms and processes
        the results.

        Args:
            search_terms (dict): A dictionary containing the search
                parameters.
            ignore_signature_match (bool): Flag to ignore publication
                signature content.
            full_text (bool): If trim result text content
            text_length (int, optional): Size of the text to be sent in the message. The default is 400.
            use_summary (bool): If exists, use summary as excerpt or full text
            conn_id (str): DOU Database Airflow conn id

        Returns:
            dict: A dictionary of processed search results.
        """

        logging.info("Search term in INLABS HOOK.")
        logging.info(f"Search terms -> {search_terms}")

        _BATCH_SIZE = 500
        texto_terms = search_terms.get("texto", [])

        if len(texto_terms) > _BATCH_SIZE:
            batches = [
                texto_terms[i : i + _BATCH_SIZE]
                for i in range(0, len(texto_terms), _BATCH_SIZE)
            ]
            seen_ids: set = set()
            hits = []
            for batch in batches:
                batch_terms = {**search_terms, "texto": batch}
                query = self._generate_opensearch_query(batch_terms)
                response = client.search(body=query, index=INDEX_NAME)
                for hit in response["hits"]["hits"]:
                    if hit["_id"] not in seen_ids:
                        seen_ids.add(hit["_id"])
                        hits.append(hit)
        else:
            query = self._generate_opensearch_query(search_terms)
            response = client.search(body=query, index=INDEX_NAME)
            hits = response["hits"]["hits"]

        logging.info("Total hits after batching: %s", len(hits))

        # Fetching results for extra edition search terms
        seen_ids = {hit["_id"] for hit in hits}
        logging.info("Seen IDs after main search: %s", seen_ids)
        extra_search_terms = self._adapt_search_terms_to_extra(
            copy.deepcopy(search_terms)
        )
        extra_texto_terms = extra_search_terms.get("texto", [])

        if len(extra_texto_terms) > _BATCH_SIZE:
            batches = [
                extra_texto_terms[i : i + _BATCH_SIZE]
                for i in range(0, len(extra_texto_terms), _BATCH_SIZE)
            ]
            for batch in batches:
                batch_terms = {**extra_search_terms, "texto": batch}
                query = self._generate_opensearch_query(batch_terms)
                response = client.search(body=query, index=INDEX_NAME)
                for hit in response["hits"]["hits"]:
                    if hit["_id"] not in seen_ids:
                        seen_ids.add(hit["_id"])
                        hits.append(hit)
        else:
            query = self._generate_opensearch_query(extra_search_terms)
            response = client.search(body=query, index=INDEX_NAME)
            for hit in response["hits"]["hits"]:
                if hit["_id"] not in seen_ids:
                    seen_ids.add(hit["_id"])
                    hits.append(hit)

        logging.info("Total hits after extra edition search: %s", len(hits))

        main_search_results = [h["_source"] for h in hits]
        all_results = pd.DataFrame(main_search_results)

        if not all_results.empty:
            all_results["pubdate"] = pd.to_datetime(
                all_results["pubdate"], format="%Y-%m-%d", errors="coerce"
            )

        # Remove the words that suceeds the delimitator !
        filtered_text_terms = self._filter_text_terms(search_terms["texto"])
        return (
            self.TextDictHandler().transform_search_results(
                ai_config=ai_config,
                ai_search_config=ai_search_config,
                response=all_results,
                text_terms=filtered_text_terms,
                ignore_signature_match=ignore_signature_match,
                full_text=full_text,
                text_length=text_length,
                use_summary=use_summary,
            )
            if not all_results.empty
            else {}
        )

    @staticmethod
    def _term_to_opensearch_qs(term: str) -> str:
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

    def _generate_opensearch_query(self, payload: dict) -> dict:
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

        pub_date = payload.get("pubdate", [date.today().strftime("%Y-%m-%d")])
        pub_date_from = pub_date[0]
        pub_date_to = pub_date[1] if len(pub_date) > 1 else pub_date_from

        filter_clauses = [
            {"range": {"pubdate": {"gte": pub_date_from, "lte": pub_date_to}}}
        ]
        must_clauses = []
        must_not_clauses = []

        filtered_dict = {
            k: payload[k] for k in payload if k in allowed_keys and payload[k]
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

    @staticmethod
    def _adapt_search_terms_to_extra(payload: dict) -> dict:
        """Modifies payload dictionary by subtracting one day of `pubdate`
        and adding `E` (for extra publication) on `pubname`.

        Args:
            payload (dict): A dictionary containing search parameters.

        Returns:
            dict: The modified payload dictionary with adapted search terms.
        """

        payload["pubdate"] = [
            (datetime.strptime(date, "%Y-%m-%d") - timedelta(days=1)).strftime(
                "%Y-%m-%d"
            )
            for date in payload["pubdate"]
        ]
        payload["pubname"] = [
            s if s.endswith("E") else s + "E" for s in payload["pubname"]
        ]

        return payload

    class TextDictHandler:
        """Handles the transformation and organization of text search
        results from the DOU Database.
        """

        def __init__(self, *args, **kwargs):
            pass

        def transform_search_results(
            self,
            ai_config: AIConfig,
            ai_search_config: AISearchConfig,
            response: pd.DataFrame,
            text_terms: list,
            ignore_signature_match: bool,
            full_text: bool = False,
            text_length: int = 400,
            use_summary: bool = False,
        ) -> dict:
            """Transforms and sorts the search results based on the presence
            of text terms and signature matching.

            Args:
                response (pd.DataFrame): The dataframe of search results
                    from the Database.
                text_terms (list): The list of text terms used in the search.
                ignore_signature_match (bool): Flag to ignore publication
                    signature content.
                full_text (bool):  If trim result text content.
                    Defaults to False.
                text_length (int): Size of the text to be sent in the message. The default is 400.
                use_summary (bool): If exists, use summary instead of
                    excerpt or full text.
                    Defaults to False

            Returns:
                dict: A dictionary of sorted and processed search results.
            """
            logging.info(f"Search results: {response}")
            df = response.copy()
            # `identifica` column is the publication title. If None
            # can be a table or other text content that is not inside
            # a publication.
            df["pubname"] = df["pubname"].apply(self._rename_section)
            df["pubdate"] = df["pubdate"].dt.strftime("%d/%m/%Y")

            # Remove duplicated title then strip HTML tags
            df["texto"] = df["texto"].apply(self._remove_duplicated_title)

            # df["texto"] = df["texto"].apply(self._remove_html_tags, full_text=full_text)
            df["texto"] = df["texto"].apply(self._remove_empty_tr)

            # Fill NaN identifica with name column value
            df["identifica"] = df["identifica"].fillna(df["name"])
            # Remove blank spaces and convert to uppercase
            df["identifica"] = df["identifica"].str.strip().str.upper()

            if any(text_terms):
                # df["matches"] = df["texto"].apply(self._find_matches, keys=text_terms)
                df["matches"] = df.apply(
                    lambda row: self._find_matches(
                        row["texto"] + " " + row["identifica"],
                        keys=text_terms,
                    ),
                    axis=1,
                )
                df["matches_assina"] = df.apply(
                    lambda row: self._normalize(row["matches"])
                    in self._normalize(row["assina"]),
                    axis=1,
                )
                df["texto"] = df.apply(
                    lambda row: self._highlight_terms(
                        [t for t in row["matches"].split(", ") if t],
                        row["texto"],
                    ),
                    axis=1,
                )
                df["identifica"] = df.apply(
                    lambda row: self._highlight_terms(
                        [t for t in row["matches"].split(", ") if t],
                        row["identifica"],
                    ),
                    axis=1,
                )
                df["count_assina"] = df.apply(
                    lambda row: (
                        row["texto"].count(row["assina"])
                        if row["assina"] is not None
                        else 0
                    ),
                    axis=1,
                )
                if ignore_signature_match:
                    df = df[~((df["matches_assina"]) & (df["count_assina"] == 1))]
            else:
                df["matches"] = ""

            if use_summary:
                # If use_summary replace texto value by summary value
                df["texto"] = df["texto"].where(df["ementa"].isnull(), df["ementa"])

            df["ai_generated"] = False

            if ai_search_config and ai_search_config.use_ai_summary:
                if use_summary:
                    # AI only where ementa not exists
                    mask = df["ementa"].isnull()
                else:
                    # AI on entire column
                    mask = df["texto"].notna()

                idx = df.loc[mask].index[: ai_search_config.ai_pub_limit]
                for i in idx:
                    df.at[i, "texto"] = AIRunner.run(
                        provider=ai_config.provider,
                        api_key=Variable.get(ai_config.api_key_var),
                        model=ai_config.model,
                        input_text=df.at[i, "texto"],
                        system_prompt=ai_search_config.ai_custom_prompt.format(
                            df.at[i, "matches"]
                        ),
                        max_tokens=ai_search_config.max_tokens,
                        temperature=ai_search_config.temperature,
                    )
                    df.at[i, "ai_generated"] = True

            df["texto"] = df.apply(
                lambda row: self._highlight_terms(
                    [t for t in row["matches"].split(", ") if t],
                    row["texto"],
                ),
                axis=1,
            )

            if not full_text:
                # Only trim text that was not processed by AI
                df.loc[~df["ai_generated"], "texto"] = df.loc[
                    ~df["ai_generated"], "texto"
                ].apply(lambda x: self._trim_text(x, text_length))

            df["display_date_sortable"] = None

            cols_rename = {
                "pubname": "section",
                "identifica": "title",
                "pdfpage": "href",
                "texto": "abstract",
                "pubdate": "date",
                "id": "id",
                "display_date_sortable": "display_date_sortable",
                "artcategory": "hierarchyList",
                "ai_generated": "ai_generated",
            }
            df.rename(columns=cols_rename, inplace=True)
            cols_output = list(cols_rename.values())

            return (
                {}
                if df.empty
                else self._group_to_dict(
                    df.sort_values(
                        by=["matches", "section", "ai_generated", "title"],
                        ascending=[True, True, False, True],
                    ),
                    "matches",
                    cols_output,
                )
            )

        @staticmethod
        def _rename_section(section: str) -> str:
            """Rename DOU Section for formatted text to notifications.

            Example:
                DO1 -> DOU - Seção 1
                DO2E -> DOU - Seção 2 Extra
            """

            # section[:2] = DO
            return section[:2] + "U - Seção " + section[2:].replace("E", " Extra")

        @staticmethod
        def _remove_html_tags(text, full_text=False) -> str:
            if isinstance(text, str):
                text_maker = html2text.HTML2Text()
                text_maker.body_width = 0
                text = text_maker.handle(text)
                # If full_text is True break lines
                separator = "<br>" if full_text else " "
                text = text.replace("\n", separator).strip()
                text = re.sub(r"\s+", " ", text)
                return text
            return ""

        def _find_matches(self, text: str, keys: list) -> str:
            """Find keys that match the text, considering normalization
            for matching and ensuring exact matches.

            Args:
                text (str): The text in which to search for keys.
                keys (list): A list of keys to be searched for in the text.
                    It's assumed that keys are strings.

            Returns:
                str: A comma-separated string of unique keys found in the text.
            """

            normalized_text = self._normalize(text)
            matches = [
                key
                for key in keys
                if re.search(
                    r"\b" + re.escape(self._normalize(key)) + r"\b",
                    normalized_text,
                    re.IGNORECASE,
                )
            ]

            return ", ".join(sorted(set(matches), key=str.lower))

        @staticmethod
        def _normalize(text: str) -> str:
            """Normalize text by removing accents and converting to
            lowercase.

            Parameters:
                text (str): The text to normalize.

            Returns:
                str: The normalized ASCII string.
            """

            return (
                unicodedata.normalize("NFKD", text)
                .encode("ascii", "ignore")
                .decode("ascii")
                .lower()
                if isinstance(text, str)
                else ""
            )

        def _highlight_terms(self, terms: list, text: str) -> str:
            """Wrap `terms` values in `text` with `<%%>` and `</%%>`.

            Matching is done against a normalized (accent-stripped) version of
            the text so that a search term like "Ministerio" also highlights
            "Ministério" in the original text.  Positions found in the normalized
            text are mapped back to the original text — this is safe because
            ``_normalize`` maps each source character to exactly one ASCII
            character (accented Latin letters, cedillas, etc.).  If the lengths
            diverge for any reason, the method falls back to direct matching.

            Args:
                terms (list): List of terms to be wrapped on text.
                text (str): String content to be updated with wrapped
                    `terms`.

            Returns:
                str: `text` with values on `terms` wrapped with `<%%>`
                    and `</%%>`.
            """

            escaped_terms = [re.escape(self._normalize(term)) for term in terms if term]
            if not escaped_terms:
                return text
            pattern = rf"\b({'|'.join(escaped_terms)})\b"

            normalized_text = self._normalize(text)

            if len(normalized_text) != len(text):
                # direct case-insensitive match on original text
                direct_pattern = rf"\b({'|'.join(re.escape(t) for t in terms if t)})\b"
                return re.sub(direct_pattern, r"<%%>\1</%%>", text, flags=re.IGNORECASE)

            result = []
            last_end = 0
            for m in re.finditer(pattern, normalized_text, flags=re.IGNORECASE):
                result.append(text[last_end : m.start()])
                result.append(f"<%%>{text[m.start() : m.end()]}</%%>")
                last_end = m.end()
            result.append(text[last_end:])

            return "".join(result)

        @staticmethod
        def _visible_len(text: str) -> int:
            """Return character count of `text` excluding HTML tags."""
            return len(re.sub(r"<[^>]+>", "", text))

        @staticmethod
        def _cut_visible_start(text: str, n: int) -> str:
            """Return the first `n` visible characters of `text`, preserving HTML tags."""
            count = 0
            i = 0
            while i < len(text) and count < n:
                if text[i] == "<":
                    end = text.find(">", i)
                    if end == -1:
                        break
                    i = end + 1
                else:
                    count += 1
                    i += 1
            return text[:i]

        @staticmethod
        def _cut_visible_end(text: str, n: int) -> str:
            """Return the last `n` visible characters of `text`, preserving HTML tags."""
            count = 0
            i = len(text)
            while i > 0 and count < n:
                if text[i - 1] == ">":
                    start = text.rfind("<", 0, i)
                    if start == -1:
                        break
                    i = start
                else:
                    count += 1
                    i -= 1
            return text[i:]

        @staticmethod
        def _truncate_from_start(text: str, text_length: int) -> tuple:
            """Take up to `text_length` non-table characters from the start of `text`.

            Tables (``<table>…</table>``) are always included in full and their
            characters are not counted toward `text_length`.

            Args:
                text (str): The source text (may contain HTML tables).
                text_length (int): Maximum number of non-table characters to keep.

            Returns:
                tuple[str, bool]: (truncated_text, was_truncated)
            """
            special_re = re.compile(
                r"<table[\s\S]*?</table>|<%%>[\s\S]*?</%%>", re.IGNORECASE
            )
            _vlen = INLABSHook.TextDictHandler._visible_len
            _cut = INLABSHook.TextDictHandler._cut_visible_start
            result = []
            char_count = 0
            last_end = 0

            def _cut_at_word_boundary(segment, cut_text):
                cut_pos = len(cut_text)
                if cut_pos < len(segment) and segment[cut_pos].isalnum():
                    cut_text = re.sub(r"\S+$", "", cut_text)
                return cut_text.rstrip()

            for m in special_re.finditer(text):
                non_special = text[last_end : m.start()]
                remaining = text_length - char_count
                if _vlen(non_special) >= remaining:
                    result.append(
                        _cut_at_word_boundary(non_special, _cut(non_special, remaining))
                    )
                    return "".join(result), True
                result.append(non_special)
                char_count += _vlen(non_special)
                result.append(m.group(0))
                last_end = m.end()

            tail = text[last_end:]
            remaining = text_length - char_count
            if _vlen(tail) > remaining:
                result.append(_cut_at_word_boundary(tail, _cut(tail, remaining)))
                return "".join(result), True

            result.append(tail)
            return "".join(result), False

        @staticmethod
        def _truncate_from_end(text: str, text_length: int) -> tuple:
            """Keep the last `text_length` non-table characters of `text`.

            Tables (``<table>…</table>``) are always included in full and their
            characters are not counted toward `text_length`.

            Highlight markers (``<%%>…</%%>``) are treated as atomic units:
            never split in the middle; their visible characters count toward
            `text_length`.

            Args:
                text (str): The source text (may contain HTML tables).
                text_length (int): Maximum number of non-table characters to keep.

            Returns:
                tuple[str, bool]: (truncated_text, was_truncated)
            """
            table_re = re.compile(r"<table[\s\S]*?</table>", re.IGNORECASE)
            marker_re = re.compile(r"<%%>[\s\S]*?</%%>")
            _vlen = INLABSHook.TextDictHandler._visible_len
            _cut = INLABSHook.TextDictHandler._cut_visible_end

            # Split into (content, seg_type) segments where seg_type is
            # 'text', 'marker', or 'table'.
            boundaries = []
            for m in table_re.finditer(text):
                boundaries.append((m.start(), m.end(), "table", m.group(0)))
            for m in marker_re.finditer(text):
                boundaries.append((m.start(), m.end(), "marker", m.group(0)))
            boundaries.sort()

            segments = []
            last_end = 0
            for start, end, seg_type, content in boundaries:
                if start > last_end:
                    segments.append((text[last_end:start], "text"))
                segments.append((content, seg_type))
                last_end = end
            if last_end < len(text):
                segments.append((text[last_end:], "text"))

            # Walk segments from the end, accumulating non-table chars
            kept = []
            char_count = 0
            was_truncated = False

            for content, seg_type in reversed(segments):
                if seg_type == "table":
                    kept.append(content)
                    continue
                if seg_type == "marker":
                    if char_count < text_length:
                        kept.append(content)
                        char_count += _vlen(content)
                    else:
                        was_truncated = True
                    continue
                remaining = text_length - char_count
                if remaining <= 0:
                    was_truncated = True
                    continue
                if _vlen(content) > remaining:
                    kept.append(_cut(content, remaining))
                    char_count += remaining
                    was_truncated = True
                else:
                    kept.append(content)
                    char_count += _vlen(content)

            kept.reverse()
            return "".join(kept), was_truncated

        def _trim_text(self, text: str, text_length: int = 400) -> str:
            """Truncates text while keeping the `<%%>` marker centered when present.

            Tables (``<table>…</table>``) are excluded from the character count and
            always rendered in full so that ``(...)`` is never inserted inside a table.

            If the text contains the `<%%>` marker, the function preserves this marker
            in the center and keeps up to `text_length` non-table characters before and
            after it.  Otherwise, it truncates from the beginning.

            Args:
                text (str): Text to be truncated (may contain HTML).
                text_length (int, optional): Max non-table characters to keep on each
                    side of the ``<%%>`` marker. Defaults to 400.

            Returns:
                str: Truncated text with ``(...)`` indicating removed parts.

            Examples:
                - With marker: ``"(...) last_N_chars<%%>first_N_chars (...)``"
                - Without marker: ``"first_N_chars (...)``"
            """
            if text_length is False or text_length is None or text_length <= 0:
                text_length = 400

            _from_start = self._truncate_from_start
            _from_end = self._truncate_from_end

            parts = text.split("<%%>", 1)

            if len(parts) > 1:
                before_full, after_full = parts[0], parts[1]

                # If <%%> is inside a table, the split above breaks the table.
                # Detect unbalanced <table> tags and reconstruct the full table.
                opens_before = len(re.findall(r"<table", before_full, re.IGNORECASE))
                closes_before = len(re.findall(r"</table>", before_full, re.IGNORECASE))

                if opens_before > closes_before:
                    open_matches = list(
                        re.finditer(r"<table", before_full, re.IGNORECASE)
                    )
                    enclosing_start = open_matches[closes_before].start()

                    depth = opens_before - closes_before
                    enclosing_end = None
                    for m in re.finditer(r"</?table", after_full, re.IGNORECASE):
                        if not m.group().startswith("</"):
                            depth += 1
                        else:
                            depth -= 1
                            if depth == 0:
                                enclosing_end = m.end()
                                break

                    if enclosing_end is not None:
                        full_table = (
                            before_full[enclosing_start:]
                            + "<%%>"
                            + after_full[:enclosing_end]
                        )
                        before_full = before_full[:enclosing_start]
                        after_full = after_full[enclosing_end:]

                        before, before_cut = _from_end(before_full, text_length)
                        after, after_cut = _from_start(after_full, text_length)

                        prefix = "(...) " if before_cut else ""
                        suffix = " (...)" if after_cut else ""

                        return f"{prefix}{before}{full_table}{after}{suffix}"

                before, before_cut = _from_end(before_full, text_length)
                after, after_cut = _from_start(after_full, text_length)

                prefix = "(...) " if before_cut else ""
                suffix = " (...)" if after_cut else ""

                return f"{prefix}{before}<%%>{after}{suffix}"
            else:
                truncated, was_cut = _from_start(text, text_length)
                return f"{truncated} (...)" if was_cut else text

        @staticmethod
        def _group_to_dict(df: pd.DataFrame, group_column: str, cols: list) -> dict:
            """Convert DataFrame grouped by a column to a dictionary.

            Args:
                df (pd.DataFrame): Input dataframe to transform.
                group_column (str): The dataframe column to group_by.
                cols (list): Filter of the cols that will remain on the
                    output dataframe.

            Returns:
                dict: Dictionary with keys as unique values of group_column
                    and values as lists of dictionaries representing the
                    selected columns.
            """

            return (
                df.groupby(group_column)
                .apply(lambda x: x[cols].apply(lambda y: y.to_dict(), axis=1).tolist())
                .to_dict()
            )

        @staticmethod
        def _remove_empty_tr(text: str) -> str:
            """Remove <tr> tags that contain no visible content."""
            soup = BeautifulSoup(text, "html.parser")

            for tr in soup.find_all("tr"):
                if all(not td.get_text(strip=True) for td in tr.find_all("td")):
                    tr.decompose()

            return str(soup)

        def _remove_duplicated_title(self, abstract: str | None) -> str:
            """Remove HTML elements with class 'identifica' from the abstract.

            The DOU the publication title both in the
            'identifica' column and as a <p class="identifica"> tag within
            the 'texto' column. This function removes the duplicated title
            from the abstract HTML to avoid redundancy.

            Args:
                abstract (str | None): The document abstract as HTML string,
                    or None.

            Returns:
                str: The abstract HTML without the 'identifica' paragraph,
                    or an empty string if abstract is None/empty.
            """

            if not abstract:
                return abstract or ""

            soup = BeautifulSoup(abstract, "html.parser")

            for tag in soup.find_all("p", class_="identifica"):
                tag.decompose()

            return str(soup)
