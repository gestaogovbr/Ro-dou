"""Apache Airflow Hook to execute DOU searches from INLABS source.
"""

import re
from datetime import datetime, timedelta, date
import pandas as pd
import unicodedata
import html2text

from airflow.hooks.base import BaseHook
from airflow.providers.postgres.hooks.postgres import PostgresHook


class INLABSHook(BaseHook):
    """A custom Apache Airflow Hook designed for executing searches via
    the DOU Postgres Database provided by INLABS.

    Attributes:
        CONN_ID (str): DOU INLABS Database Airflow conn id.
    """

    CONN_ID = "inlabs_db"

    def __init__(self, *args, **kwargs):
        pass

    def search_text(
        self,
        search_terms: dict,
        ignore_signature_match: bool,
        conn_id: str = CONN_ID,
    ) -> dict:
        """Searches the DOU Database with the provided search terms and processes
        the results.

        Args:
            search_terms (dict): A dictionary containing the search
                parameters.
            ignore_signature_match (bool): Flag to ignore publication
                signature content.
            conn_id (str): DOU Database Airflow conn id

        Returns:
            dict: A dictionary of processed search results.
        """

        hook = PostgresHook(conn_id)

        # Fetching results for main search terms
        main_search_queries = self._generate_sql(search_terms)
        hook.run(main_search_queries["create_extension"], autocommit=True)
        main_search_results = hook.get_pandas_df(main_search_queries["select"])

        # Fetching results for yesterday extra search terms
        extra_search_terms = self._adapt_search_terms_to_extra(search_terms)
        extra_search_queries = self._generate_sql(extra_search_terms)
        extra_search_results = hook.get_pandas_df(extra_search_queries["select"])

        # Combining main and extra search results
        all_results = pd.concat(
            [main_search_results, extra_search_results], ignore_index=True
        )

        return (
            self.TextDictHandler().transform_search_results(
                all_results, search_terms["texto"], ignore_signature_match
            )
            if not all_results.empty
            else {}
        )

    @staticmethod
    def _generate_sql(payload: dict) -> str:
        """Generates SQL query based on a dictionary of lists. The
        dictionary key is the table column and the dictionary values
        are a list of the terms to filter.

        Args:
            payload (dict): A dictionary containing search parameters.
                example = {
                    "texto": ["Termo 1", "Termo 2"],
                    "pubdate": ["2024-04-01", "2024-04-01"]
                    "pubname": ["DO1"]
                }

        Returns:
            str: The generated SQL query.
        """

        allowed_keys = [
            "name",
            "pubname",
            "artcategory",
            "identifica",
            "titulo",
            "subtitulo",
            "texto",
        ]
        filtered_dict = {k: payload[k] for k in payload if k in allowed_keys}

        pub_date = payload.get("pubdate", [date.today().strftime("%Y-%m-%d")])
        pub_date_from = pub_date[0]
        try:
            pub_date_to = pub_date[1]
        except IndexError:
            pub_date_to = pub_date_from

        query = f"SELECT * FROM dou_inlabs.article_raw WHERE (pubdate BETWEEN '{pub_date_from}' AND '{pub_date_to}')"

        conditions = []
        for key, values in filtered_dict.items():
            key_conditions = " OR ".join(
                [
                    rf"dou_inlabs.unaccent({key}) ~* dou_inlabs.unaccent('\y{value}\y')"
                    for value in values
                ]
            )
            conditions.append(f"({key_conditions})")

        if conditions:
            query = f"{query} AND {' AND '.join(conditions)}"

        queries = {
            "create_extension": "CREATE EXTENSION IF NOT EXISTS unaccent SCHEMA dou_inlabs",
            "select": query,
        }

        return queries

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
            self, response: pd.DataFrame, text_terms: list, ignore_signature_match: bool
        ) -> dict:
            """Transforms and sorts the search results based on the presence
            of text terms and signature matching.

            Args:
                response (pd.DataFrame): The dataframe of search results
                    from the Database.
                text_terms (list): The list of text terms used in the search.
                ignore_signature_match (bool): Flag to ignore publication
                    signature content.

            Returns:
                dict: A dictionary of sorted and processed search results.
            """

            df = response.copy()
            df.dropna(subset=["identifica"], inplace=True)
            df["pubname"] = df["pubname"].apply(self._rename_section)
            df["identifica"] = df["identifica"].apply(self._remove_html_tags)
            df["pubdate"] = df["pubdate"].dt.strftime("%d/%m/%Y")
            df["texto"] = df["texto"].apply(self._remove_html_tags)
            df["matches"] = df["texto"].apply(self._find_matches, keys=text_terms)
            df["matches_assina"] = df.apply(
                lambda row: self._normalize(row["matches"])
                in self._normalize(row["assina"]),
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
            df["texto"] = df.apply(
                lambda row: self._highlight_terms(
                    row["matches"].split(", "), row["texto"]
                ),
                axis=1,
            )
            df["texto"] = df["texto"].apply(self._trim_text)
            df["display_date_sortable"] = None
            df["hierarchyList"] = None

            if ignore_signature_match:
                df = df[~((df["matches_assina"]) & (df["count_assina"] == 1))]

            cols_rename = {
                "pubname": "section",
                "identifica": "title",
                "pdfpage": "href",
                "texto": "abstract",
                "pubdate": "date",
                "id": "id",
                "display_date_sortable": "display_date_sortable",
                "hierarchyList": "hierarchyList",
            }
            df.rename(columns=cols_rename, inplace=True)
            cols_output = list(cols_rename.values())

            return (
                {}
                if df.empty
                else self._group_to_dict(
                    df.sort_values(by="matches"), "matches", cols_output
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
        def _remove_html_tags(text) -> str:
            if isinstance(text, str):
                text = html2text.HTML2Text().handle(text).replace("\n", " ").strip()
                text = re.sub(r"\s+", " ", text)
                return text
            return ""

        def _find_matches(self, text: str, keys: list) -> list:
            """Find keys that match the text, considering normalization
            for matching and ensuring exact matches.

            Args:
                text (str): The text in which to search for keys.
                keys (list): A list of keys to be searched for in the text.
                    It's assumed that keys are strings.

            Returns:
                list: A sorted list of unique keys found in the text.
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

            return ", ".join(sorted(set(matches)))

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
        def _highlight_terms(terms: list, text: str) -> str:
            """Wrap `terms` values in `text` with `<%%>` and `</%%>`.

            Args:
                terms (list): List of terms to be wrapped on text.
                text (str): String content to be updated with wrapped
                    `terms`.

            Returns:
                str: `text` with values on `terms` wrapped with `<%%>`
                    and `</%%>`.
            """

            escaped_terms = [re.escape(term) for term in terms]
            pattern = rf"\b({'|'.join(escaped_terms)})\b"
            highlighted_text = re.sub(
                pattern, r"<%%>\1</%%>", text, flags=re.IGNORECASE
            )

            return highlighted_text

        @staticmethod
        def _trim_text(text: str) -> str:
            """Get a len(x) string and returns len(400) keeping `<%%>`
            at the center.
            """

            parts = text.split("<%%>", 1)
            return (
                "(...) " + parts[0][-200:] + "<%%>" + parts[1][:200] + " (...)"
                if len(parts) > 1
                else text[:400] + " (...)"
            )

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