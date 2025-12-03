"""
API Hooks for querying the Official Gazette (Diário Oficial da União)
"""
import sys
import os
import logging
from datetime import datetime
import time
import json
from typing import List
import requests

from airflow.hooks.base import BaseHook

from bs4 import BeautifulSoup

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
from utils.search_domains import SearchDate, Field, Section, calculate_from_datetime


class DOUHook(BaseHook):
    IN_WEB_BASE_URL = "https://www.in.gov.br/web/dou/-/"
    IN_API_BASE_URL = "https://www.in.gov.br/consulta/-/buscar/dou"
    SEC_DESCRIPTION = {
        Section.SECAO_1.value: "Seção 1",
        Section.SECAO_2.value: "Seção 2",
        Section.SECAO_3.value: "Seção 3",
        Section.EDICAO_EXTRA.value: "Edição Extra",
        Section.EDICAO_EXTRA_1A.value: "Seção: 1 - Extra A",
        Section.EDICAO_EXTRA_1B.value: "Seção: 1 - Extra B",
        Section.EDICAO_EXTRA_1D.value: "Seção: 1 - Extra D",
        Section.EDICAO_EXTRA_2A.value: "Seção: 2 - Extra A",
        Section.EDICAO_EXTRA_2B.value: "Seção: 2 - Extra B",
        Section.EDICAO_EXTRA_2D.value: "Seção: 2 - Extra D",
        Section.EDICAO_EXTRA_3A.value: "Seção: 3 - Extra A",
        Section.EDICAO_EXTRA_3B.value: "Seção: 3 - Extra B",
        Section.EDICAO_EXTRA_3D.value: "Seção: 3 - Extra D",
        Section.EDICAO_SUPLEMENTAR.value: "Edição Suplementar",
        Section.TODOS.value: "Todas",
    }

    def __init__(self, *args, **kwargs):
        pass

    def _get_query_str(self, term, field, is_exact_search):
        """
        For terms with more than one word,
        add double quotes at the beginning and end
        """
        if is_exact_search:
            term = f'"{term}"'

        if field == Field.TUDO:
            return term
        else:
            return f"{field.value}-{term}"

    
    def _request_page(self, with_retry: bool, payload: dict):
        # Cabeçalhos melhorados
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; Ro-DOU/0.7; +https://github.com/gestaogovbr/Ro-dou)",
            "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
            "Cache-Control": "no-cache",
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
        }

        try:
            # Primeira tentativa com HTTPS
            response = requests.get(self.IN_API_BASE_URL, params=payload, headers=headers, timeout=10)

            # Validação extra: garantir que não caiu para HTTP
            if not response.url.startswith("https://"):
                logging.warning("Resposta redirecionada para HTTP! URL final: %s", response.url)

            response.raise_for_status()
            return response

        except requests.exceptions.SSLError as ssl_err:
            logging.error("Erro SSL ao acessar via HTTPS: %s", ssl_err)
            logging.info("Tentando fallback para HTTP...")

            # Fallback para HTTP
            http_url = self.IN_API_BASE_URL.replace("https://", "http://")
            try:
                response = requests.get(http_url, params=payload, headers=headers, timeout=10)
                response.raise_for_status()
                logging.warning("Usando HTTP como fallback. URL final: %s", response.url)
                return response
            except requests.exceptions.RequestException as e:
                logging.error("Erro também no fallback HTTP: %s", e)
                raise

        except requests.exceptions.RequestException as e:
            logging.error("Erro geral ao acessar DOU API: %s", e)
            if with_retry:
                logging.info("Tentando novamente em 30 segundos...")
                time.sleep(30)
                return requests.get(self.IN_API_BASE_URL, params=payload, headers=headers, timeout=10)
       





    def search_text(
        self,
        search_term: str,
        sections: List[Section],
        reference_date: datetime = datetime.now(),
        search_date=SearchDate.DIA,
        field=Field.TUDO,
        is_exact_search=True,
        with_retry=True,
    ):
        """
        Search for a term in the API and return all ocurrences.

        Args:
            - search_term: The term to perform the search with.
            - section: The Journal section to perform the search on.

        Return:
            - A list of dicts of structred results.
        """

        publish_from = calculate_from_datetime(reference_date, search_date)

        payload = {
            "q": self._get_query_str(search_term, field, is_exact_search),
            "exactDate": "personalizado",
            "publishFrom": publish_from.strftime("%d-%m-%Y"),
            "publishTo": reference_date.strftime("%d-%m-%Y"),
            "sortType": "0",
            "s": [section.value for section in sections],
        }
        #Verify payload content
        logging.info("Payload content: %s", payload)
        page = self._request_page(payload=payload, with_retry=with_retry)

        soup = BeautifulSoup(page.content, "html.parser")

        # Checks if there is more than one page of results
        pagination_tag = soup.find(
            'button', id='lastPage'
        )

        if (pagination_tag) is not None:
            # Get the number of pages in the pagination bar
            number_pages = int(pagination_tag.text.strip())
        else:
            # issue https://github.com/gestaogovbr/Ro-dou/issues/101
            second_page_tag = soup.find(
                'button', id='2btn'
            )
            if second_page_tag:
                number_pages = 2
            else:
                # If is a single page
                number_pages = 1

        logging.info("Total pages: %s", number_pages)

        all_results = []
        last_item = None

        # Loop for each page of result
        for page_num in range(number_pages):
            logging.info("Searching in page %s", str(page_num + 1))

            # If there is more than one page add extra payload params and reload the page
            if page_num > 0 and last_item:
                # The id is needed for pagination to work because it requires
                # passing the last id from the previous item page in request URL
                # Delta is the number of records per page. By now is restricted up to 20.
                payload.update({
                    "id": last_item["id"],
                    "displayDate": last_item["display_date_sortable"],
                    # "delta": 20,
                    "newPage": page_num + 1,
                    "currentPage": page_num,
                })

                page = self._request_page(payload=payload, with_retry=with_retry)
                soup = BeautifulSoup(page.content, "html.parser")

            script_tag = soup.find(
                "script", id="_br_com_seatecnologia_in_buscadou_BuscaDouPortlet_params"
            )

            if script_tag is None:
                logging.error(
                    "Script tag with ID '_br_com_seatecnologia_in_buscadou_BuscaDouPortlet_params' not found in DOU response. "
                    "The DOU API may have changed its structure."
                )
                logging.info("HTML content received: %s", page.content)
                raise ValueError(
                    "Unable to find search results in DOU response."
                    "The DOU API may have changed its structure."
                )

            search_results = json.loads(script_tag.contents[0])["jsonArray"]

            if search_results:
                for content in search_results:
                    item = {
                        "section": content["pubName"].lower(),
                        "title": content["title"],
                        "href": self.IN_WEB_BASE_URL + content["urlTitle"],
                        "abstract": content["content"],
                        "date": content["pubDate"],
                        "id": content["classPK"],
                        "display_date_sortable": content["displayDateSortable"],
                        "hierarchyList": content["hierarchyList"],
                        "hierarchyStr": content["hierarchyStr"],
                        "arttype": content["artType"],
                        }

                    all_results.append(item)
                    last_item = item

        return all_results