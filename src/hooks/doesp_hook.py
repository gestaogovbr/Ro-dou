"""
Hook for Diário Oficial do Estado de São Paulo (DOESP).

This module implements DOESPHook.search_text with the same signature used by DOUHook
so it can be plugged into the existing searcher flow. The exact JSON structure of the
DOESP search API may vary; this implementation tries to be resilient and is documented
so you can adapt selectors quickly.
"""

import logging
import time
from datetime import datetime
from typing import List, Optional

import requests
try:
    from bs4 import BeautifulSoup
except Exception:
    BeautifulSoup = None

try:
    from airflow.hooks.base import BaseHook
except Exception:
    # Allow running tests without Airflow installed
    BaseHook = object

from utils.search_domains import SearchDate, Field, calculate_from_datetime, SectionDOESP


class DOESPHook(BaseHook):
    """Hook to query the DOESP public search API.

    Notes:
    - This uses the discovered journals endpoint to map "cadernos" (seções) to ids.
    - The main search endpoint used here is an API endpoint discovered in the site
      (may need adjustment if the API changes).
    """

    BASE_WEB_URL = "https://doe.sp.gov.br/"
    JOURNALS_API_URL = "https://do-api-web-search.doe.sp.gov.br/v2/journals"
    SEARCH_API_URL = "https://do-api-web-search.doe.sp.gov.br/v2/advanced-search/publications"

    def __init__(self, *args, **kwargs):
        super().__init__()

    def _request(self, url: str, params: Optional[dict] = None, headers: Optional[dict] = None, with_retry: bool = True, timeout: int = 10):
        hdrs = {
            "User-Agent": "Mozilla/5.0 (compatible; Ro-DOU/0.7; +https://github.com/gestaogovbr/Ro-dou)",
            "Accept": "application/json, text/plain, */*",
        }
        if headers:
            hdrs.update(headers)

        try:
            r = requests.get(url, params=params, headers=hdrs, timeout=timeout)
            r.raise_for_status()
            return r
        except requests.exceptions.RequestException as e:
            logging.error("Request error to %s: %s", url, e)
            if with_retry:
                time.sleep(5)
                r = requests.get(url, params=params, headers=hdrs, timeout=timeout)
                r.raise_for_status()
                return r
            raise

    def _get_journal_map(self, timeout: int = 5):
        """Return dict mapping journal name -> id. Empty dict on error."""
        try:
            r = self._request(self.JOURNALS_API_URL, timeout=timeout)
            data = r.json()
            items = data.get("items", []) if isinstance(data, dict) else []
            return {it.get("name"): it.get("id") for it in items if it.get("id") and it.get("name")}
        except Exception as e:
            logging.warning("Could not fetch DOESP journals: %s", e)
            return {}

    def _parse_item(self, item: dict):
        """Generic item parser: adapt to exact API fields if needed."""
        # Try common field names
        title = item.get("title") or item.get("name") or item.get("headline")
        href = item.get("slug") or item.get("url") or item.get("path") or item.get("link")
        if href and not href.startswith("http"):
            href = self.BASE_WEB_URL + href
        snippet = item.get("snippet") or item.get("excerpt") or item.get("summary") or item.get("content") or ""
        # Date fields may be 'date', 'publishedAt', 'publicationDate'
        date_raw = item.get("date") or item.get("publishedAt") or item.get("publicationDate") or item.get("createdAt")
        date_str = ""
        if date_raw:
            try:
                # try ISO
                date_str = datetime.fromisoformat(str(date_raw).split("Z")[0]).strftime("%d/%m/%Y")
            except Exception:
                # fallback, just present as-is
                date_str = str(date_raw)

        return {
            "title": title,
            "href": href,
            "abstract": snippet,
            "date": date_str,
            "id": item.get("id") or item.get("uuid") or None,
            "section": item.get("journalName") or item.get("journal") or "DOESP",
            "display_date_sortable": date_raw or date_str,
            "hierarchyList": item.get("hierarchy") or [],
            "hierarchyStr": item.get("hierarchyStr") or "",
            "arttype": item.get("type") or item.get("artType") or "",
        }

    def search_text(
        self,
        search_term: str,
        journals: List = None,  # expect list of caderno names or ids
        reference_date: datetime = datetime.now(),
        search_date=SearchDate.DIA,
        with_retry=True,
    ):
        """Perform search against DOESP.

        journals: list of journal names (e.g. "Executivo") or journal ids.
        Returns list of dicts with keys similar to DOUHook.search_text results.
        """
        publish_from = calculate_from_datetime(reference_date, search_date)

        # Prepare journals parameter: map names to ids if possible
        journal_ids = []
        if journals:
            # fetch map
            journal_map = self._get_journal_map()
            for s in journals:
                # skip dict-like overrides handled later
                if isinstance(s, dict):
                    continue
                if s == "TODOS":
                    journal_ids = []
                    break
                # if user passed an id already, keep
                if isinstance(s, str) and s in journal_map.values():
                    journal_ids.append(s)
                elif isinstance(s, str):
                    # try mapping by name
                    mapped = journal_map.get(s)
                    if mapped:
                        journal_ids.append(mapped)

        # Build querystring parameters compatible with the DOE-SP API observed in the site
        params = {
            "PageNumber": 1,
            "PageSize": 20,
            "SortField": "Date",
            # Period parameter used by site
            "periodStartingDate": publish_from.strftime("%Y-%m-%d"),
            # From/To dates
            "FromDate": publish_from.strftime("%Y-%m-%d"),
            "ToDate": reference_date.strftime("%Y-%m-%d"),
        }

        # Terms can be a single string or a list/tuple. API expects indexed params: Terms[0]=..., Terms[1]=...
        if isinstance(search_term, (list, tuple)):
            for idx, t in enumerate(search_term):
                params[f"Terms[{idx}]"] = t
        elif search_term:
            params["Terms[0]"] = search_term

        # If journals contains dict-like overrides (SectionId, PublicationTypeId, JournalId), apply them
        if journals:
            for s in journals:
                if isinstance(s, dict):
                    # copy supported keys
                    for key in ("SectionId", "PublicationTypeId", "JournalId"):
                        if s.get(key):
                            params[key] = s.get(key)

        # If journal ids are present and JournalId not already set, the API accepts JournalId (single)
        if journal_ids and not params.get("JournalId"):
            # use first id if multiple (API example shows single JournalId param)
            params["JournalId"] = journal_ids[0]

        logging.info("DOESP search payload: %s", params)

        resp = self._request(self.SEARCH_API_URL, params=params, with_retry=with_retry)

        # Try parse JSON
        try:
            data = resp.json()
            # Try common containers
            items = data.get("items") or data.get("results") or data.get("hits") or []
            results = []
            for it in items:
                results.append(self._parse_item(it))
            return results
        except ValueError:
            # Fallback to HTML parsing
            if BeautifulSoup is None:
                raise RuntimeError("BeautifulSoup not installed and response is HTML. Install beautifulsoup4 to enable HTML parsing")
            soup = BeautifulSoup(resp.text, "html.parser")
            # Find result blocks - adapt selector to real HTML
            blocks = soup.select(".result, .search-result, .result-item")
            results = []
            for node in blocks:
                title_node = node.select_one(".title a, a.result-link")
                title = title_node.get_text(strip=True) if title_node else (node.select_one(".title").get_text(strip=True) if node.select_one(".title") else "")
                href = title_node["href"] if title_node and title_node.has_attr("href") else None
                snippet_node = node.select_one(".snippet, .excerpt")
                snippet = snippet_node.decode_contents() if snippet_node else ""
                date_node = node.select_one(".date, .published")
                date_txt = date_node.get_text(strip=True) if date_node else ""
                id_attr = node.get("data-id") or node.get("id")
                results.append({
                    "title": title,
                    "href": href if href and href.startswith("http") else (self.BASE_WEB_URL + href if href else None),
                    "abstract": snippet,
                    "date": date_txt,
                    "id": id_attr,
                    "section": "DOESP",
                    "display_date_sortable": date_txt,
                    "hierarchyList": [],
                    "hierarchyStr": "",
                    "arttype": "",
                })
            return results