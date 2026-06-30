"""Legacy SQL mode for INLABS searches.

This module keeps the pre-OpenSearch implementation isolated while the main
``inlabs_hook`` decides which backend to use through an environment flag.
"""

import copy
import logging
import re
from datetime import date

import pandas as pd
from airflow.providers.postgres.hooks.postgres import PostgresHook  # type: ignore

from .inlabs_hook import INLABSHook


class INLABSSQLModeHook(INLABSHook):
    """Execute INLABS searches directly against PostgreSQL."""

    def search_text(
        self,
        ai_config: dict,
        ai_search_config: dict,
        search_terms: dict,
        ignore_signature_match: bool,
        full_text: bool,
        text_length: int,
        use_summary: bool,
        ignore_attachments: bool = False,
        show_relevancy: bool = False,
        conn_id: str = INLABSHook.CONN_ID,
        client = None,
    ) -> dict:
        """Search INLABS using the legacy SQL query path."""
        hook = PostgresHook(conn_id)

        logging.info("Search term in INLABS SQL mode.")
        logging.info("Search terms -> %s", search_terms)

        main_search_queries = self._generate_sql(search_terms)
        hook.run(main_search_queries["create_extension"], autocommit=True)
        main_search_results = hook.get_pandas_df(main_search_queries["select"])

        extra_search_terms = self._adapt_search_terms_to_extra(
            copy.deepcopy(search_terms)
        )
        extra_search_queries = self._generate_sql(extra_search_terms)
        extra_search_results = hook.get_pandas_df(extra_search_queries["select"])

        all_results = pd.concat(
            [main_search_results, extra_search_results], ignore_index=True
        )

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
                show_relevancy=show_relevancy,
            )
            if not all_results.empty
            else {}
        )

    @staticmethod
    def _generate_sql(payload: dict) -> dict:
        """Generate legacy SQL queries for INLABS search terms."""
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
        filtered_dict = {k: payload[k] for k in payload if k in allowed_keys}

        pub_date = payload.get("pubdate", [date.today().strftime("%Y-%m-%d")])
        pub_date_from = pub_date[0]
        pub_date_to = pub_date[1] if len(pub_date) > 1 else pub_date_from

        query = (
            "SELECT * FROM dou_inlabs.article_raw "
            f"WHERE (pubdate BETWEEN '{pub_date_from}' AND '{pub_date_to}')"
        )

        term_operators = ["&", "!", "|", "(", ")"]

        conditions = []
        for key, values in filtered_dict.items():
            if key == "texto":
                if any(values):
                    key_conditions = []
                    for term in values:
                        if any(operator in term for operator in term_operators):
                            operator_str = "".join(term_operators)
                            sub_terms = re.split(rf"\s*([{operator_str}])\s*", term)
                            sub_terms = [
                                sub_term for sub_term in sub_terms if sub_term.strip()
                            ]

                            sub_conditions = []
                            like_positive = True
                            for sub_term in sub_terms:
                                if sub_term in term_operators:
                                    if sub_term in {"&", "!"}:
                                        like_positive = sub_term != "!"
                                        operator = " AND "
                                    elif sub_term == "|":
                                        like_positive = True
                                        operator = " OR "
                                    elif sub_term in {"(", ")"}:
                                        like_positive = True
                                        operator = sub_term
                                    sub_conditions.append(operator)
                                else:
                                    operator = "~*" if like_positive else "!~*"
                                    sub_conditions.append(
                                        rf"dou_inlabs.unaccent({key}) {operator} dou_inlabs.unaccent('\y{sub_term}\y')",
                                    )

                            key_conditions.append("(" + "".join(sub_conditions) + ")")

                        else:
                            key_conditions.append(
                                rf"dou_inlabs.unaccent({key}) ~* dou_inlabs.unaccent('\y{term}\y')"
                            )

                    conditions.append("(" + " OR ".join(key_conditions) + ")")

            elif key == "artcategory_ignore":
                conditions.append(
                    "("
                    + " AND ".join(
                        [
                            rf"dou_inlabs.unaccent(artcategory) !~* dou_inlabs.unaccent('^{value}')"
                            for value in values
                        ]
                    )
                    + ")"
                )
            elif key == "terms_ignore":
                conditions.append(
                    "("
                    + " AND ".join(
                        [
                            rf"dou_inlabs.unaccent(texto) !~* dou_inlabs.unaccent('\y{value}\y')"
                            for value in values
                        ]
                    )
                    + ")"
                )
            else:
                conditions.append(
                    "("
                    + " OR ".join(
                        [
                            rf"dou_inlabs.unaccent({key}) ~* dou_inlabs.unaccent('\y{value}\y')"
                            for value in values
                        ]
                    )
                    + ")"
                )

        if conditions:
            query = f"{query} AND {' AND '.join(conditions)}"

        logging.info("Generated SQL Query:")
        logging.info(query)

        return {
            "create_extension": "CREATE EXTENSION IF NOT EXISTS unaccent SCHEMA dou_inlabs",
            "select": query,
        }
