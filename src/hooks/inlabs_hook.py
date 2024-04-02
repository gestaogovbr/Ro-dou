"""Apache Airflow Hook to execute DOU searches from INLABS source.
"""

import os
import logging
import re
from datetime import datetime, timedelta
import time
import json
from collections.abc import Iterator
import unicodedata
import math
import requests
from requests import Response
import html2text

from airflow.hooks.base import BaseHook


class INLABSHook(BaseHook):
    """A custom Apache Airflow Hook designed for executing searches via
    the DOU API provided by INLABS.

    Attributes:
        DOU_API_URL (str): URL of the DOU API to send requests to.
        DOU_API_REQUEST_CHUNKSIZE (str): Size of chunks to split the
            search terms into for batch processing.
    """

    DOU_API_URL = os.getenv("DOU_API_URL", "http://dou-api:5057/dou")
    DOU_API_REQUEST_CHUNKSIZE = int(os.getenv("DOU_API_REQUEST_CHUNKSIZE", "100"))
    MAX_RETRIES = 3
    RETRY_DELAY = 2

    def __init__(self, *args, **kwargs):
        pass

    def search_text(self, search_terms: dict, ignore_signature_match: bool) -> dict:
        """Searches the DOU API with the provided search terms and processes
        the results.

        Args:
            search_terms (dict): A dictionary containing the search
                parameters.
            ignore_signature_match (bool): Flag to ignore publication
                signature content.

        Returns:
            dict: A dictionary of processed search results.
        """

        response = []
        text_terms = search_terms["texto"]

        for index, chunk in enumerate(
            self._iterate_in_chunks(text_terms, self.DOU_API_REQUEST_CHUNKSIZE), start=1
        ):
            search_terms["texto"] = chunk
            logging.info(
                "Loading chunk: %s of %s",
                index,
                math.ceil(len(text_terms) / self.DOU_API_REQUEST_CHUNKSIZE),
            )
            retries = 0
            while retries < self.MAX_RETRIES:
                try:
                    r = self._request_api_data(search_terms)
                    r.raise_for_status()
                    response.extend(r.json())

                    r = self._request_api_data(
                        self._adapt_search_terms_to_extra(search_terms)
                    )
                    r.raise_for_status()
                    response.extend(r.json())
                    break
                except (
                    requests.exceptions.ReadTimeout,
                    requests.exceptions.HTTPError,
                ) as e:
                    retries += 1
                    logging.info(
                        "Timeout occurred, retrying %s of %s...",
                        retries,
                        self.MAX_RETRIES,
                    )
                    time.sleep(self.RETRY_DELAY)
                    if retries == self.MAX_RETRIES:
                        raise TimeoutError() from e

        return (
            self.TextDictHandler().transform_search_results(
                response, text_terms, ignore_signature_match
            )
            if response
            else {}
        )

    @staticmethod
    def _iterate_in_chunks(lst: list, chunk_size: int) -> Iterator[list]:
        """Splits a list into chunks of a specified size.
        """

        for i in range(0, len(lst), chunk_size):
            yield lst[i : i + chunk_size]

    def _request_api_data(self, payload: dict) -> Response:
        headers = {"Content-Type": "application/json"}
        post_result = requests.post(
            self.DOU_API_URL,
            headers=headers,
            data=json.dumps(payload),
            timeout=45,
        )

        print(post_result.json())

        return post_result

    @staticmethod
    def _adapt_search_terms_to_extra(payload: dict) -> dict:
        payload["pub_date"] = [
            (datetime.strptime(date, "%Y-%m-%d") - timedelta(days=1)).strftime(
                "%Y-%m-%d"
            )
            for date in payload["pub_date"]
        ]
        payload["pub_name"] = [
            s if s.endswith("E") else s + "E" for s in payload["pub_name"]
        ]

        return payload

    class TextDictHandler:
        """Handles the transformation and organization of text search
        results from the DOU API.
        """

        def __init__(self, *args, **kwargs):
            pass

        def transform_search_results(
            self, response: list, text_terms: list, ignore_signature_match: bool
        ) -> dict:
            """Transforms and sorts the search results based on the presence
            of text terms and signature matching.

            Args:
                response (list): The list of search results from the API.
                text_terms (list): The list of text terms used in the search.
                ignore_signature_match (bool): Flag to ignore publication
                    signature content.

            Returns:
                dict: A dictionary of sorted and processed search results.
            """

            all_results = {}
            # sort by publication title (from api called `identifica`)
            sorted_data = sorted(
                response, key=lambda x: x["identifica"] if x["identifica"] else ""
            )
            for content in sorted_data:
                item = {
                    "section": self._rename_section(content["pub_name"]),
                    "title": self._remove_html_tags(content["identifica"]),
                    "href": content["pdf_page"],
                    "abstract": self._remove_html_tags(content["texto"]),
                    "date": self._format_date(content["pub_date"]),
                    "id": content["article_id"],
                    "display_date_sortable": None,
                    "hierarchyList": None,
                }

                #XXX check here
                matches = self._find_matches(item["abstract"], text_terms)

                if matches and item["title"]:
                    matches_n = [self._normalize(v) for v in matches]
                    # The signature text cames inside the columns `texto`
                    # (signature + content) and `assina` (only the signature).
                    # So if tagged to ignore_signature_match, is checked
                    # if the signature in the `texto` and `assina` columns
                    # are the same and that the signature only appears
                    # one time at `texto` column.
                    if not (
                        ignore_signature_match
                        and self._normalize(item["abstract"]).count(
                            self._normalize(content["assina"])
                        )
                        == 1
                        and self._normalize(content["assina"]) in matches_n
                    ):
                        item["abstract"] = self._highlight_terms(
                            matches, item["abstract"]
                        )
                        item["abstract"] = self._trim_text(item["abstract"])
                        all_results = self._update_nested_dict(
                            all_results, ", ".join(matches), item
                        )

            sorted_dict = {k: all_results[k] for k in sorted(all_results)}

            return sorted_dict

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

        @staticmethod
        def _format_date(date: str) -> str:
            return datetime.strptime(date, "%Y-%m-%d").strftime("%d/%m/%Y")

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

            return sorted(set(matches))

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
        def _update_nested_dict(dict_to_update: dict, key: str, value: dict) -> dict:
            """Append value to dictionary existent key or create new key
            with value if not exists.

            Args:
                dict_to_update (dict): Dictionary to update key, values.
                key (str): Dictionary key to add or update.
                value (dict): Value/content of the key.

            Returns:
                dict: Updated dictionary.

            Example:
                input ({}, "key1", "value1")
                output ({"key1": ["value1"]})
                input ({"key1": ["value1"]}, "key1", "value2")
                output ({"key1": ["value1", "value2"]})
                input ({"key1": ["value1", "value2"]}, "key2", "value3")
                output ({"key1": ["value1", "value2"], "key2": ["value3"]})
            """

            if key in dict_to_update:
                dict_to_update[key].append(value)
            else:
                dict_to_update[key] = [value]

            return dict_to_update
