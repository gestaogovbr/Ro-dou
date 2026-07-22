"""Apache Airflow Hook to execute DOU searches from INLABS source."""

import copy
import os
import re
import logging
from datetime import datetime, timedelta
import unicodedata
import pandas as pd
import html2text

from airflow.hooks.base import BaseHook  # type: ignore

# from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.models import Variable  # type: ignore

from typing import Optional
from schemas import AIConfig, AISearchConfig, NeuralSearchConfig  # type: ignore
from ai.runner import AIRunner

from ro_dou_src.utils.open_search.client_open_search import OpenSearchClient  # type: ignore
from ro_dou_src.utils.open_search.config import (  # type: ignore
    INDEX_NAME,
    RO_DOU_INLABS_USE_OPENSEARCH,
)
from ro_dou_src.utils.open_search.query_builder import OpenSearchQueryBuilder  # type: ignore
from opensearchpy import OpenSearch  # type: ignore

from bs4 import BeautifulSoup

# arttype values that identify annexes/attachments in the INLABS index.
_ATTACHMENT_ARTTYPE = frozenset({"ANEXO", "QUADRO", "TABELA"})


class INLABSHook(BaseHook):
    """A custom Apache Airflow Hook designed for executing searches via
    the DOU Postgres Database provided by INLABS.

    Attributes:
        CONN_ID (str): DOU INLABS Database Airflow conn id.
    """

    CONN_ID = "inlabs_db"

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
        neural_search_config: Optional[NeuralSearchConfig] = None,
        ignore_attachments: bool = False,
        ignore_inline_tables: bool = False,
        min_table_rows: int = 1,
        show_relevancy: bool = False,
        conn_id: str = CONN_ID,
        client: OpenSearch | None = None,
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
            show_relevancy (bool): If True, include a relevancy tag in the report for each result
            neural_search_config (NeuralSearchConfig, optional): Controls whether
                keyword matching is combined with semantic (vector) similarity
                when querying OpenSearch, and the score threshold/result cap for
                the semantic part. Defaults to a config with ``neural_search=False``.
            conn_id (str): DOU Database Airflow conn id

        Returns:
            dict: A dictionary of processed search results.
                Terms found in each hit are taken from OpenSearch
                ``matched_queries`` and propagated to ``matched_terms`` and the
                legacy ``matches`` field.
        """

        if RO_DOU_INLABS_USE_OPENSEARCH.lower() != "true":
            from .inlabs_hook_sql_mode import INLABSSQLModeHook

            logging.info(
                "OpenSearch disabled. Using INLABS SQL mode.",
            )
            return INLABSSQLModeHook().search_text(
                ai_config=ai_config,
                ai_search_config=ai_search_config,
                search_terms=search_terms,
                ignore_signature_match=ignore_signature_match,
                full_text=full_text,
                text_length=text_length,
                use_summary=use_summary,
                ignore_attachments=ignore_attachments,
                ignore_inline_tables=ignore_inline_tables,
                min_table_rows=min_table_rows,
                show_relevancy=show_relevancy,
                conn_id=conn_id,
            )

        if client is None:
            client = OpenSearchClient().get_client()

        neural_config = neural_search_config or NeuralSearchConfig()
        neural_search = bool(neural_config.neural_search)

        search_terms = {
            **search_terms,
            "neural_search": neural_search,
            "min_score": neural_config.score,
        }

        logging.info("Search term in INLABS HOOK.")
        logging.info(f"Search terms -> {search_terms}")

        _BATCH_SIZE = 500
        texto_terms = search_terms.get("texto", [])

        logging.info(f"Text terms -> {texto_terms}")
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

        searched_expression = ", ".join(search_terms.get("texto", []))
        main_search_results = [
            self._map_opensearch_hit(
                h, searched_expression=searched_expression, neural_search=neural_search
            )
            for h in hits
        ]

        if neural_search and main_search_results:
            # A hit's `_score` is the sum of whichever `should` clauses
            # matched. Keyword (BM25-like) scores and the semantic knn score
            # (0-1 range for cosinesimil) live on completely different
            # scales, so they must be reported separately — mixing them into
            # one min/max/mean makes the average meaningless for calibrating
            # NEURAL_SEARCH_MIN_SCORE.
            semantic_only_scores = [
                r["score"]
                for r in main_search_results
                if not r.get("matched_terms") and r.get("score") is not None
            ]
            keyword_scores = [
                r["score"]
                for r in main_search_results
                if r.get("matched_terms") and r.get("score") is not None
            ]
            logging.info(
                "Neural search checkpoint: %d hits totais (%d via palavra-chave, "
                "%d somente por similaridade semântica; score mínimo=%s)",
                len(main_search_results),
                len(keyword_scores),
                len(semantic_only_scores),
                neural_config.score,
            )
            if semantic_only_scores:
                logging.info(
                    "  score semântico (comparável ao threshold): min=%.3f "
                    "max=%.3f mean=%.3f",
                    min(semantic_only_scores),
                    max(semantic_only_scores),
                    sum(semantic_only_scores) / len(semantic_only_scores),
                )
            if keyword_scores:
                logging.info(
                    "  score com match textual (escala BM25, não comparável "
                    "ao threshold): min=%.3f max=%.3f mean=%.3f",
                    min(keyword_scores),
                    max(keyword_scores),
                    sum(keyword_scores) / len(keyword_scores),
                )
            # Per-hit breakdown, weakest score first: the borderline hits
            # near the configured score threshold are what matters for tuning it.
            for r in sorted(main_search_results, key=lambda r: r.get("score") or 0):
                logging.info(
                    "  score=%.3f matched_terms=%s id=%s identifica=%.80r",
                    r.get("score") or 0.0,
                    r.get("matched_terms") or "[]",
                    r.get("id"),
                    r.get("identifica"),
                )

            # Radial search has no result-count cap (mutually exclusive with
            # `k` in OpenSearch), so cap semantic-only hits here, keeping
            # only the highest-scoring ones. Keyword-matched hits are never
            # affected.
            max_semantic_results = neural_config.max_semantic_results
            semantic_only_hits = [
                r for r in main_search_results if not r.get("matched_terms")
            ]
            if len(semantic_only_hits) > max_semantic_results:
                keyword_hits = [
                    r for r in main_search_results if r.get("matched_terms")
                ]
                semantic_only_hits.sort(key=lambda r: r.get("score") or 0, reverse=True)
                dropped = len(semantic_only_hits) - max_semantic_results
                logging.info(
                    "Neural search: descartados %d resultados somente "
                    "semânticos além do limite de %d",
                    dropped,
                    max_semantic_results,
                )
                main_search_results = (
                    keyword_hits + semantic_only_hits[:max_semantic_results]
                )

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
                ignore_attachments=ignore_attachments,
                ignore_inline_tables=ignore_inline_tables,
                min_table_rows=min_table_rows,
                show_relevancy=show_relevancy,
                neural_search=neural_search,
            )
            if not all_results.empty
            else {}
        )

    @staticmethod
    def _generate_opensearch_query(payload: dict) -> dict:
        """Build the OpenSearch query body for an INLABS search payload."""
        qb = OpenSearchQueryBuilder()
        qb.payload = payload
        return qb.build()

    @staticmethod
    def _matched_terms_from_hit(hit: dict) -> list:
        """Return sorted matched terms reported by OpenSearch for one hit."""
        return sorted(set(hit.get("matched_queries", [])), key=str.lower)

    @classmethod
    def _map_opensearch_hit(
        cls,
        hit: dict,
        searched_expression: str = "",
        neural_search: bool = False,
    ) -> dict:
        """Map an OpenSearch hit to the dataframe shape used by notifications.

        Matched terms come exclusively from ``hit["matched_queries"]``. The
        legacy ``matches`` field is populated from the same source for backward
        compatibility. ``semantic_match`` is True when the hit has no keyword
        match at all, i.e. it was only found through vector similarity.
        """
        matched_terms = cls._matched_terms_from_hit(hit)
        highlights = hit.get("highlight", {}).get("texto_plain", [])
        return {
            **hit.get("_source", {}),
            "score": hit.get("_score"),
            "searched_expression": searched_expression,
            "matched_terms": matched_terms,
            "matched_terms_text": ", ".join(matched_terms),
            "matches": ", ".join(matched_terms),
            "opensearch_highlights": highlights,
            "semantic_match": bool(neural_search and not matched_terms),
        }

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
            has_ementa: bool = False,
            ignore_attachments: bool = False,
            ignore_inline_tables: bool = False,
            min_table_rows: int = 1,
            show_relevancy: bool = False,
            neural_search: bool = False,
        ) -> dict:
            """Transforms and sorts the search results based on the presence
            of matched terms reported by OpenSearch and signature matching.

            Args:
                response (pd.DataFrame): The dataframe of search results
                    from OpenSearch. When present, ``matched_terms`` must come
                    from hit ``matched_queries``.
                text_terms (list): The list of text terms used in the search.
                ignore_signature_match (bool): Flag to ignore publication
                    signature content.
                full_text (bool):  If trim result text content.
                    Defaults to False.
                text_length (int): Size of the text to be sent in the message. The default is 400.
                use_summary (bool): If exists, use summary instead of
                    excerpt or full text.
                    Defaults to False
                neural_search (bool): If True, the search will be performed using semantic search techniques (vectorization).

            Returns:
                dict: A dictionary of sorted and processed search results.
            """
            # Semantic hits may have no lexical `matched_terms`, so the
            # relevancy tag becomes the only visible relevance signal.
            show_relevancy = show_relevancy or neural_search

            # When semantic search is enabled, ignore attachments and
            # inline tables to avoid false positives from unrelated content.
            ignore_attachments = ignore_attachments or neural_search
            ignore_inline_tables = ignore_inline_tables or neural_search

            logging.info(f"Search results: {response}")
            df = response.copy()
            # `identifica` column is the publication title. If None
            # can be a table or other text content that is not inside
            # a publication.
            df["pubname"] = df["pubname"].apply(self._rename_section)
            df["pubdate"] = df["pubdate"].dt.strftime("%d/%m/%Y")

            # Remove duplicated title then strip HTML tags
            df["texto"] = df["texto"].apply(self._remove_duplicated_title)

            df["texto"] = df["texto"].apply(self._remove_empty_tr)

            if ignore_inline_tables:
                df["texto"] = df["texto"].apply(
                    lambda x: self._replace_inline_tables(x, min_table_rows)
                )

            if "opensearch_highlights" in df.columns:
                df["_has_opensearch_highlight"] = df["opensearch_highlights"].apply(
                    self._has_opensearch_highlight
                )
            else:
                df["_has_opensearch_highlight"] = False

            if ignore_attachments:
                # A blank/null `identifica` means this record is a table or
                # other fragment attached to a publication, not the
                # publication itself (see comment above). This is the
                # authoritative signal; `arttype` is kept as a secondary,
                # defense-in-depth check.
                _is_attachment = (
                    df["identifica"].isna()
                    | (df["identifica"].astype(str).str.strip() == "")
                    | df["arttype"].str.upper().isin(_ATTACHMENT_ARTTYPE)
                )
                df = df[~_is_attachment]
                if df.empty:
                    return {}

            # Fill NaN identifica with name column value
            df["identifica"] = df["identifica"].fillna(df["name"])
            # Remove blank spaces and convert to uppercase
            df["identifica"] = df["identifica"].str.strip().str.upper()

            should_process_matches = "matched_terms" in df.columns or any(text_terms)

            if "matched_terms" in df.columns:
                df["matched_terms"] = df["matched_terms"].apply(
                    lambda terms: (
                        sorted(set(terms), key=str.lower)
                        if isinstance(terms, list)
                        else []
                    )
                )
                df["matched_terms_text"] = df["matched_terms"].apply(
                    lambda terms: ", ".join(terms)
                )
                df["matches"] = df["matched_terms_text"]
                if (
                    "semantic_match" in df.columns
                    and "searched_expression" in df.columns
                ):
                    # Pure semantic hits have no lexical `matched_terms`, so
                    # `matches` would otherwise be empty and the result would
                    # be grouped/labeled under a blank term in the report.
                    # Fall back to the full set of configured search terms.
                    semantic_only = df["semantic_match"] & (df["matches"] == "")
                    df.loc[semantic_only, "matches"] = df.loc[
                        semantic_only, "searched_expression"
                    ]
            elif any(text_terms):
                df["matches"] = df.apply(
                    lambda row: self._find_matches(
                        row["texto"] + " " + row["identifica"],
                        keys=text_terms,
                    ),
                    axis=1,
                )
            elif "matches" not in df.columns:
                df["matches"] = ""

            if should_process_matches:
                df["matches_assina"] = df.apply(
                    lambda row: self._normalize(row["matches"])
                    in self._normalize(row["assina"]),
                    axis=1,
                )
                df["texto"] = df.apply(
                    lambda row: self._highlight_search_text(
                        [t for t in row["matches"].split(", ") if t],
                        row["texto"],
                        (
                            row["opensearch_highlights"]
                            if row["_has_opensearch_highlight"]
                            else []
                        ),
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

            def _highlight_row_matches(row):
                if "<%%>" in row["texto"]:
                    return row["texto"]
                return self._highlight_terms(
                    [t for t in row["matches"].split(", ") if t],
                    row["texto"],
                )

            if "has_ementa" not in df.columns:
                df["has_ementa"] = has_ementa

            if "full_text" not in df.columns:
                df["full_text"] = full_text

            if use_summary:
                # If use_summary replace texto value by summary value
                ementa_has_content = df["ementa"].fillna("").str.strip().ne("")
                df["texto"] = df["texto"].where(~ementa_has_content, df["ementa"])
                # The ementa replaces `texto` after the inline-table handling at
                # the top of this method, so re-apply it here; otherwise the
                # placeholder inserted earlier would be discarded along with the
                # original `texto`.
                if ignore_inline_tables:
                    df.loc[ementa_has_content, "texto"] = df.loc[
                        ementa_has_content, "texto"
                    ].apply(lambda x: self._replace_inline_tables(x, min_table_rows))
                # Mark if the ementa exists in a new column to be used on the template to display the "Ementa" tag
                df["has_ementa"] = ementa_has_content
                df.loc[ementa_has_content, "texto"] = df.loc[ementa_has_content].apply(
                    _highlight_row_matches, axis=1
                )

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
                    df.at[i, "texto"] = _highlight_row_matches(df.loc[i])

            if not full_text:
                # Only trim text that was not processed by AI and does not have ementa
                mask = (~df["ai_generated"]) & (~df["has_ementa"])

                df.loc[mask, "texto"] = df.loc[mask, "texto"].apply(
                    lambda x: self._trim_text(x, text_length)
                )

            df["display_date_sortable"] = None

            if "score" not in df.columns:
                df["score"] = None
            if "show_relevancy" not in df.columns:
                df["show_relevancy"] = show_relevancy
            if "semantic_match" not in df.columns:
                df["semantic_match"] = False

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
                "has_ementa": "has_ementa",
                "full_text": "full_text",
                "score": "score",
                "show_relevancy": "show_relevancy",
                "semantic_match": "semantic_match",
            }
            if "matched_terms" in df.columns:
                cols_rename["matched_terms"] = "matched_terms"
            if "matched_terms_text" in df.columns:
                cols_rename["matched_terms_text"] = "matched_terms_text"
            if "searched_expression" in df.columns:
                cols_rename["searched_expression"] = "searched_expression"
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
            """Find configured keys in text using normalized exact matching."""
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

        @staticmethod
        def _has_opensearch_highlight(highlights) -> bool:
            """Return True when OpenSearch returned at least one highlight."""
            return isinstance(highlights, list) and any(highlights)

        @classmethod
        def _opensearch_highlight_excerpt(cls, text: str, highlights) -> str:
            """Return OpenSearch highlighted snippets when available.

            OpenSearch highlights mark the actual analyzed match in the
            document, including morphological variants such as a plural form
            matched by a singular search term. Keeping those markers allows
            ``_trim_text`` to center the notification excerpt on the real hit.
            """
            if not cls._has_opensearch_highlight(highlights):
                return text
            return " (...) ".join(highlights)

        @staticmethod
        def _plain_text(text: str) -> str:
            """De-tag and collapse whitespace, mirroring the ``texto_plain``
            field indexed in OpenSearch (see ``open_search.indexer``)."""
            return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", text)).strip()

        @classmethod
        def _drop_omitted_table_highlights(cls, text: str, highlights):
            """Discard OpenSearch highlight fragments whose content was removed
            by ``ignore_inline_tables``.

            OpenSearch highlights come from ``texto_plain`` (the fully de-tagged
            document), so a term matched *inside* an omitted table would
            otherwise resurface the table content and bypass the
            ``[Tabela de N linhas omitida]`` placeholder. When a table was
            omitted from ``text`` (the placeholder is present), keep only the
            fragments whose text still exists in the cleaned ``text``.
            """
            if not cls._has_opensearch_highlight(highlights):
                return highlights
            if 'class="placeholder"' not in text:
                return highlights
            haystack = cls._normalize(cls._plain_text(text))
            return [
                h
                for h in highlights
                if cls._normalize(
                    cls._plain_text(h.replace("<%%>", "").replace("</%%>", ""))
                )
                in haystack
            ]

        def _highlight_search_text(
            self, terms: list, text: str, opensearch_highlights=None
        ) -> str:
            """Highlight matched terms, falling back to OpenSearch snippets.

            Local highlighting is preferred to avoid OpenSearch highlighter
            marking broad analyzer tokens from the whole query. The OpenSearch
            highlight is used only when local highlighting cannot mark the
            configured term, which covers morphological variants.
            """
            highlighted_text = self._highlight_terms(terms, text)
            if "<%%>" in highlighted_text:
                return highlighted_text
            highlights = self._drop_omitted_table_highlights(
                text, opensearch_highlights
            )
            return self._opensearch_highlight_excerpt(text, highlights)

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

            # When there is no search highlight to center on (e.g. the match
            # was inside a table removed by ``ignore_inline_tables``), anchor the
            # excerpt on the omitted-table placeholder so the
            # ``[Tabela de N linhas omitida]`` marker stays visible instead of
            # being truncated away with the surrounding text.
            if "<%%>" not in text:
                placeholder_match = re.search(
                    r'<p><span class="placeholder">\[[^\]]*\]</span></p>', text
                )
                if placeholder_match:
                    before_full = text[: placeholder_match.start()]
                    placeholder = placeholder_match.group(0)
                    after_full = text[placeholder_match.end() :]
                    before, before_cut = _from_end(before_full, text_length)
                    after, after_cut = _from_start(after_full, text_length)
                    prefix = "(...) " if before_cut else ""
                    suffix = " (...)" if after_cut else ""
                    return f"{prefix}{before}{placeholder}{after}{suffix}"

            marker_match = re.search(r"<%%>[\s\S]*?</%%>", text)
            if marker_match and self._visible_len(marker_match.group(0)) > text_length:
                before_full = text[: marker_match.start()]
                opens_before = len(re.findall(r"<table", before_full, re.IGNORECASE))
                closes_before = len(re.findall(r"</table>", before_full, re.IGNORECASE))

                if opens_before == closes_before:
                    marker = marker_match.group(0)
                    after_full = text[marker_match.end() :]
                    before, before_cut = _from_end(before_full, text_length)
                    after, after_cut = _from_start(after_full, text_length)

                    prefix = "(...) " if before_cut else ""
                    suffix = " (...)" if after_cut else ""

                    return f"{prefix}{before}{marker}{after}{suffix}"

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
        def _replace_inline_tables(text: str, min_table_rows: int = 1) -> str:
            """Replace inline <table> blocks with a short placeholder.

            Only tables with at least ``min_table_rows`` rows (after empty-row
            removal) are replaced. With the default of 1, every table with
            content is omitted; a higher ``min_table_rows`` keeps smaller tables
            that likely carry structural content (e.g. a two-column value/label
            pair). Applies regardless of ``full_text``.
            """
            soup = BeautifulSoup(text, "html.parser")
            for table in soup.find_all("table"):
                rows = table.find_all("tr")
                if len(rows) >= min_table_rows:
                    n = len(rows)
                    label = f"[Tabela de {n} linhas omitida]"
                    placeholder = BeautifulSoup(
                        f'<p><span class="placeholder">{label}</span></p>',
                        "html.parser",
                    )
                    table.replace_with(placeholder)
            return str(soup)

        @staticmethod
        def _remove_empty_tr(text: str) -> str:
            """Remove <tr> tags that contain no visible content.

            Both ``<td>`` and ``<th>`` cells are inspected so that a header row
            (built only with ``<th>``) is not mistaken for an empty row. This
            keeps such rows counted toward ``min_table_rows`` in
            ``_replace_inline_tables``.
            """
            soup = BeautifulSoup(text, "html.parser")

            for tr in soup.find_all("tr"):
                cells = tr.find_all(["td", "th"])
                if all(not cell.get_text(strip=True) for cell in cells):
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
