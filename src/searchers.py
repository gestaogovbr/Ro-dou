"""Abstract and concrete classes to perform terms searchs.
"""

import ast
import json
import logging
import re
import time
import sys
import os
from abc import ABC
from datetime import datetime, timedelta
from random import random
from typing import Dict, List, Tuple, Union
import string
import pandas as pd
import requests
from unidecode import unidecode
from bs4 import BeautifulSoup

from typing import Optional

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from hooks.dou_hook import DOUHook
from hooks.inlabs_hook import INLABSHook
from utils.search_domains import (
    Field,
    SearchDate,
    Section,
    SectionINLABS,
    calculate_from_datetime,
)

class BaseSearcher(ABC):
    SCRAPPING_INTERVAL = 1
    CLEAN_HTML_RE = re.compile("<.*?>")

    def _cast_term_list(self, pre_term_list: Dict[list, str]) -> list:
        """Convert different term list formats to a standardized list.
        
        Handles the conversion of search terms from various sources:
        - Returns empty list if input is None
        - Returns list as-is if already a list
        - Returns string as-is if it's a string
        - Converts JSON string to list by reading as DataFrame and extracting first column
        
        Args:
            pre_term_list: Search terms in various formats (list, str, JSON string, or None)
            
        Returns:
            list: Standardized list of search terms, empty list if input is None
        """
        
        if pre_term_list is None:
            return []
        elif isinstance(pre_term_list, list):
            return pre_term_list        
        # elif isinstance(pre_term_list, str):
        #     return pre_term_list
        else:
            return pd.read_json(pre_term_list).iloc[:, 0].tolist()

        # return (
        #     pre_term_list
        #     if isinstance(pre_term_list, list)
        #     else pd.read_json(pre_term_list).iloc[:, 0].tolist()
        # )

    def _group_results(
        self,
        search_results: dict,
        term_list: Dict[list, str],
        department: list[str] = None,
    ) -> dict:
        """Produces a grouped result based on departments and group name.
        If `term_list` is already  the list of terms or it is a string received through xcom
        from `select_terms_from_db` task and the sql_query returned a
        second column (used as the group name)
        """

        dpt_grouped_result = self._group_by_department(search_results, department)

        if isinstance(term_list, str) and len(ast.literal_eval(term_list).values()) > 1:
            grouped_result = self._group_by_term_group(dpt_grouped_result, term_list)
        else:
            grouped_result = {"single_group": dpt_grouped_result}

        return grouped_result

    @staticmethod
    def _group_by_term_group(search_results: dict, term_n_group: str) -> dict:
        """Rebuild the dict grouping the results based on term_n_group
        mapping
        """
        dict_struct = ast.literal_eval(term_n_group)
        terms, groups = dict_struct.values()
        term_group_map = dict(zip(terms.values(), groups.values()))

        grouped_result = {}
        for k, v in search_results.items():
            group = term_group_map[k.split(",")[0]]
            update = {k: v}

            if group in grouped_result:
                grouped_result[group].update(update)
            else:
                grouped_result[group] = update

        sorted_dict = {key: grouped_result[key] for key in sorted(grouped_result)}

        return sorted_dict

    @staticmethod
    def _group_by_department(search_results: dict, department: list) -> dict:
        dpt_grouped_result = {}
        # Iterate over all terms under the group
        for term, results in search_results.items():
            # Initialize the department group for this term
            dpt_grouped_result[term] = {}

            for result in results:
                # change all units in hierarchyList to lower case
                # for unit in result['hierarchyList']:
                if department:
                    for dept in department:
                        if dept.casefold() in str(result["hierarchyList"]).casefold():
                            # Initialize the group if not present
                            if dept not in dpt_grouped_result[term]:
                                dpt_grouped_result[term][dept] = []
                            dpt_grouped_result[term][dept].append(result)
                else:
                    dpt_grouped_result[term].setdefault("single_department", [])
                    dpt_grouped_result[term]["single_department"].append(result)

        search_results = dpt_grouped_result

        return search_results

    def _really_matched(self, search_term: str, abstract: str) -> bool:
        """Verify if the term returned from the API matches the search terms.
        This function is useful for filtering API results to include only close matches, not exact matches.
        """
        whole_match = self._clean_html(abstract).replace("... ", "")
        norm_whole_match = self._normalize(whole_match)

        norm_term = self._normalize(search_term)

        return norm_term in norm_whole_match

    def _clean_html(self, raw_html: str) -> str:
        clean_text = re.sub(self.CLEAN_HTML_RE, "", raw_html)
        return clean_text

    def _normalize(self, raw_str: str) -> str:
        """Remove characters (accents and other not alphanumeric) lower
        it and keep only one space between words"""
        KEEPCHAR = string.punctuation + "—–"
        text = unidecode(raw_str).lower()
        text = "".join(c if c.isalnum() or c in KEEPCHAR else " " for c in text)
        text = " ".join(text.split())
        return text


class DOUSearcher(BaseSearcher):
    SPLIT_MATCH_RE = re.compile(r"(.*?)<.*?>(.*?)<.*?>")
    dou_hook = DOUHook()

    def exec_search(
        self,
        term_list,
        dou_sections: List[str],
        search_date,
        field,
        is_exact_search: bool,
        ignore_signature_match: bool,
        force_rematch: bool,
        department: List[str],
        department_ignore: List[str],
        pubtype: List[str],
        reference_date: datetime,
    ):
        search_results = self._search_all_terms(
            self._cast_term_list(term_list),
            dou_sections,
            search_date,
            reference_date,
            field,
            is_exact_search,
            ignore_signature_match,
            force_rematch,
            department,
            department_ignore,
            pubtype
        )
        group_results = self._group_results(search_results, term_list, department)

        return group_results

    def _search_all_terms(
        self,
        term_list,
        dou_sections,
        search_date,
        trigger_date,
        field,
        is_exact_search,
        ignore_signature_match,
        force_rematch,
        department,
        department_ignore,
        pubtype
    ) -> dict:
        search_results = {}
        logging.info(f"Starting search with terms: {term_list}")
        # if no terms are specified, the search filter will search for all terms (*) to apply the filters
        if not term_list:
            logging.info("No specific terms provided, searching all")
            term_list = ["*"]

        for search_term in term_list:
            logging.info("Starting search for term: %s", search_term)

            # To perform a search without specifying terms, use the broad search function
            search_term = "" if search_term == "*" else search_term

            results = self._search_text_with_retry(
                search_term=search_term,
                sections=[Section[s] for s in dou_sections],
                reference_date=trigger_date,
                search_date=SearchDate[search_date],
                field=Field[field],
                is_exact_search=is_exact_search,
            )

            # In cases where no terms are specified, skip the matching checks
            if search_term != "":
                if ignore_signature_match:
                    results = [
                        r
                        for r in results
                        if not self._is_signature(search_term, r.get("abstract"), r.get("href"))
                    ]
                if force_rematch:
                    results = [
                        r
                        for r in results
                        if self._really_matched(search_term, r.get("abstract"))
                    ]

            if department or department_ignore:
                self._match_department(results, department, department_ignore)

            if pubtype:
                self._match_pubtype(results, pubtype)

            self._render_section_descriptions(results)

            self._add_standard_highlight_formatting(results)

            if results:
                # To execute a search without terms, use the key "all_publications"
                result_key = "all_publications" if search_term == "" else search_term
                search_results[result_key] = results

            time.sleep(self.SCRAPPING_INTERVAL * random() * 2)

        return search_results

    def _add_standard_highlight_formatting(self, results: list) -> None:
        for result in results:
            result["abstract"] = (
                result["abstract"]
                .replace("<span class='highlight' style='background:#FFA;'>", "<%%>")
                .replace("</span>", "</%%>")
            )

    def _search_text_with_retry(
        self,
        search_term,
        sections,
        reference_date,
        search_date,
        field,
        is_exact_search,
        max_retries=5,
    ) -> list:

        retry = 1

        while True:
            try:
                return self.dou_hook.search_text(
                    search_term=search_term,
                    sections=sections,
                    reference_date=reference_date,
                    search_date=search_date,
                    field=field,
                    is_exact_search=is_exact_search,
                )
            except:
                import requests
                # If the underlying error is SSL related, don't retry — likely permanent
                exc_type, exc_value, _ = sys.exc_info()
                if isinstance(exc_value, requests.exceptions.SSLError):
                    logging.error("SSL error encountered for term '%s' — aborting retries: %s", search_term, exc_value)
                    raise

                if retry > max_retries:
                    logging.error("Error - Max retries reached")
                    raise

                logging.info("Attempt %s of %s for term '%s'", retry, max_retries, search_term)
                logging.info("Sleeping for 30 seconds before retry dou_hook.search_text().")
                time.sleep(30)
                retry += 1

    def _is_signature(self, search_term: str, abstract: str, document_href: str = None) -> bool:
        """This function checks if the search_term (usually used to search for people's names)
        is present in the signature. To achieve this, the function takes advantage of a "bug" in the API.
        In such cases, the value returns as abstract and begins with the document signature.
        This does not happen when the match occurs in other parts of the document.
        With this approach, the function checks if this situation occurs
        and is used to filter results present in the final document.
        This function corrects cases where a person's name forms a larger part of another name.
        For example, the name 'ANTONIO DE OLIVEIRA' is part of the name 'JOSÉ ANTONIO DE OLIVEIRA MATOS'.
        
        When the API returns an incorrect abstract (combining different parts of the document),
        this method will fetch the full document to verify if the name at the beginning of the
        abstract is actually the document signature or appears elsewhere in the content.
        """
        clean_abstract = self._clean_html(abstract)
        start_name, match_name = self._get_prior_and_matched_name(abstract)

        norm_abstract = self._normalize(clean_abstract)
        norm_abstract_without_start_name = norm_abstract[len(start_name) :]
        norm_term = self._normalize(search_term)

        basic_signature_check = (
            # Approve the signature only if it contains uppercase letters.
            (start_name + match_name).isupper()
            and
            # Fix the cases '`ANTONIO DE OLIVEIRA`' and
            # '`ANTONIO DE OLIVEIRA` MATOS'
            (
                norm_abstract.startswith(norm_term)
                or
                # Fix the cases 'JOSÉ `ANTONIO DE OLIVEIRA`' and
                # ' JOSÉ `ANTONIO DE OLIVEIRA` MATOS'
                norm_abstract_without_start_name.startswith(norm_term)
            )
        )
        
        # If basic check indicates signature, but we have document href, verify with full document
        if basic_signature_check and document_href:
            return self._verify_signature_in_full_document(search_term, abstract, document_href)
        
        return basic_signature_check

    def _verify_signature_in_full_document(self, search_term: str, abstract: str, document_href: str) -> bool:
        """Verify if the search term appearing at the beginning of the abstract is actually
        a signature by fetching and analyzing the full document content.
        
        Args:
            search_term: The term being searched for
            abstract: The abstract from the API result
            document_href: URL to the full document
            
        Returns:
            bool: True if the term is likely a signature, False otherwise
        """
        try:
            # Fetch the full document
            response = requests.get(document_href, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract the main content text from the document
            # The DOU document content is typically in specific tags
            content_divs = soup.find_all(['div', 'p'], class_=lambda x: x and ('text' in x.lower() or 'content' in x.lower()))
            if not content_divs:
                # Fallback: get all text content
                full_text = soup.get_text()
            else:
                full_text = ' '.join([div.get_text() for div in content_divs])
            
            # Normalize the full document text
            norm_full_text = self._normalize(full_text)
            norm_term = self._normalize(search_term)
            
            # Check if the term appears in the document content (not just signature)
            term_positions = []
            start = 0
            while True:
                pos = norm_full_text.find(norm_term, start)
                if pos == -1:
                    break
                term_positions.append(pos)
                start = pos + 1
            
            # If the term appears multiple times or not at the very beginning, 
            # it's likely not just a signature
            if len(term_positions) > 1:
                return False
            
            # If the term only appears once and it's at the very beginning,
            # it's likely a signature
            if len(term_positions) == 1 and term_positions[0] < 100:
                return True
                
            # If term doesn't appear in full document, but appears in abstract,
            # the abstract is probably corrupted (as described in the issue)
            if len(term_positions) == 0:
                logging.warning(f"Term '{search_term}' found in abstract but not in full document. "
                              f"Document: {document_href}")
                return False
                
            return False
            
        except Exception as e:
            logging.warning(f"Failed to fetch full document for signature verification: {e}. "
                          f"Falling back to basic signature check for document: {document_href}")
            # Fallback to original logic if we can't fetch the document
            return True

    def _match_department(self, results: list, department: list = None, department_ignore: list = None) -> list:
        """Applies the filter to the results returned by the units
        listed in the 'department' parameter in the YAML.
        """
        if department:
            logging.info("Applying filter for department list")
            logging.info(department)
        if department_ignore:
            logging.info("Applying filter for department_ignore list")
            logging.info(department_ignore)
        for result in results[:]:
            if department is not None:
                if not any(dpt in result["hierarchyList"] for dpt in department):
                    results.remove(result)
            if department_ignore is not None:
                if any(dpt in result["hierarchyStr"] for dpt in department_ignore):
                    results.remove(result)
    def _match_pubtype(self, results: list, pubtype: list) -> list:
        """Applies the filter to the results returned by the publications type listed
        in the 'pubtype' parameter in the YAML.
        """
        logging.info("Applying filter for pubtype list")
        logging.info(pubtype)
        for result in results[:]:
            if not any(pub in result["arttype"] for pub in pubtype):
                results.remove(result)

    def _get_prior_and_matched_name(self, raw_html: str) -> Tuple[str, str]:
        groups = self.SPLIT_MATCH_RE.match(raw_html).groups()
        return groups[0], groups[1]

    def _render_section_descriptions(self, results: list) -> list:
        for result in results:
            result["section"] = f"DOU - {DOUHook.SEC_DESCRIPTION[result['section']]}"


class QDSearcher(BaseSearcher):

    API_BASE_URL = "https://queridodiario.ok.org.br/api/gazettes"

    def exec_search(
        self,
        territory_id,
        term_list,
        is_exact_search: bool,
        reference_date: datetime,
        excerpt_size: int,
        number_of_excerpts: int,
        result_as_email: bool = True,
    ):
        term_list = self._cast_term_list(term_list)
        tailored_date = reference_date - timedelta(days=1)
        search_results = {}

        for search_term in term_list:

            results = self._search_term(
                territory_id=territory_id,
                search_term=search_term,
                is_exact_search=is_exact_search,
                reference_date=tailored_date,
                excerpt_size=excerpt_size,
                number_of_excerpts=number_of_excerpts,
                result_as_email=result_as_email,
            )
            if results:
                search_results[search_term] = results
            time.sleep(self.SCRAPPING_INTERVAL * random() * 2)

        return self._group_results(search_results, term_list)

    def _search_term(
        self,
        territory_id,
        search_term,
        is_exact_search,
        reference_date,
        excerpt_size,
        number_of_excerpts,
        result_as_email: bool = True,
    ) -> list:
        payload = _build_query_payload(
            search_term,
            is_exact_search,
            reference_date,
            territory_id,
            excerpt_size,
            number_of_excerpts
        )

        req_result = requests.get(self.API_BASE_URL, params=payload)

        parsed_results = [
            self.parse_result(result, result_as_email)
            for result in json.loads(req_result.content)["gazettes"]
        ]

        return parsed_results

    def parse_result(self, result: dict, result_as_email: bool = True) -> dict:
        section = (
            "extraordinária" if result.get("is_extra_edition", False) else "ordinária"
        )
        if result_as_email:
            abstract = (
                "<p>" + "</p><p>".join(result["excerpts"]).replace("\n", "") + "</p>"
            )
        else:
            abstract = "\n".join(result["excerpts"]).replace("\n", "")
        return {
            "section": f"QD - Edição {section} ",
            "title": (
                "Município de " f"{result['territory_name']} - {result['state_code']}"
            ),
            "href": result["url"],
            "abstract": abstract,
            "date": datetime.strptime(result["date"], "%Y-%m-%d").strftime("%d/%m/%Y"),
        }


def _build_query_payload(
    search_term: str,
    is_exact_search: bool,
    reference_date: datetime,
    territory_id,
    excerpt_size: int = 250,
    number_of_excerpts: int = 3
) -> List[tuple]:
    if is_exact_search:
        search_term = f'"{search_term}"'

    size = 100
    payload_territory_id = []
    if territory_id:
        if isinstance(territory_id, int): territory_id = [territory_id]
        for terr_id in territory_id:
            payload_territory_id.append(("territory_ids", terr_id))
        # The search filter is applied using only a date,
        # and the result returns a maximum of one edition per country(township).
        size = len(territory_id)

    payload =  [
        ("size", size),
        ("excerpt_size", excerpt_size),
        ("sort_by", "relevance"),
        ("pre_tags", "<%%>"),
        ("post_tags", "</%%>"),
        ("number_of_excerpts", number_of_excerpts),
        ("published_since", reference_date.strftime("%Y-%m-%d")),
        ("published_until", reference_date.strftime("%Y-%m-%d")),
        ("querystring", search_term),
    ]
    return payload + payload_territory_id


class INLABSSearcher(BaseSearcher):
    """
    A searcher class that interfaces with an Airflow INLABSHook to perform
    DOU searches with various filters such as `terms`, `sections`, `dates`,
    and `departments`.
    """

    def exec_search(
        self,
        terms: Union[List[str], str],
        dou_sections: List[str],
        search_date: str,
        department: List[str],
        department_ignore: List[str],
        ignore_signature_match: bool,
        full_text: bool,
        text_length: Optional[int],
        use_summary: bool,
        pubtype: List[str],
        reference_date: datetime = datetime.now(),
    ) -> Dict:
        """
        Execute a search with given parameters, applying filters and
        transforming terms as needed.

        Args:
            terms (Union[List[str], str]): Search terms as a List or a
                string formatted as a dict (when from sql query).
            dou_sections (List[str]): List of DOU sections to filter the search.
                dou_sections examples: SECAO_1, SECAO_3D, EDICAO_EXTRA_1
            search_date (str): Date interval filter.
                search_date examples: DIA, SEMANA, MES, ANO
            department (List[str]): List of departments to filter the search.
            department_ignore (List[str]): List of departments to be ignored in the search.
            ignore_signature_match (bool): Flag to ignore publication
                signature content.
            full_text (bool): If trim result text content 
            text_length (int, optional): Size of the text to be sent in the message. The default is 400.           
            use_summary (bool): If exists, use summary as excerpt or full text
            pubtype (List[str]): List of publication types to filter the search.
            reference_date (datetime, optional): Reference date for the
                search. Defaults to now.

        Returns:
            Dict: Grouped search results.
        """

        inlabs_hook = INLABSHook()
        search_terms = self._prepare_search_terms(terms)
        search_terms = self._apply_filters(
            search_terms, dou_sections, department, department_ignore, pubtype, reference_date, search_date
        )

        search_results = inlabs_hook.search_text(
            search_terms, ignore_signature_match, full_text, text_length, use_summary
        )

        group_results = self._group_results(search_results, terms, department)

        return group_results

    def _prepare_search_terms(self, terms: Union[List[str], str]) -> Dict:
        """Prepare search terms based on input terms.

        Args:
            terms (Union[List[str], str]): Can be one of:
                String formatted as dictionary when comes from a database
                query
                List when comes from `terms` key of the .yaml
                None when no specific terms are provided
        Returns:
            Dict: Formatted as {"texto": List of terms}
        """
        
        if not terms:
            #  Searches without specific terms = search for all terms
            return {"texto": [""]}
        elif isinstance(terms, List):
            return {"texto": terms}
        elif isinstance(terms, str) and terms.startswith("["):            
            return {"texto": ast.literal_eval(terms)}        
        return {"texto": self._split_sql_terms(json.loads(terms))}

    def _apply_filters(
        self,
        search_terms: Dict,
        sections: List[str],
        department: List[str],
        department_ignore: List[str],
        pubtype: List[str],
        reference_date: datetime,
        search_date: str,
    ):
        """Apply `sections`, `departments`, `pubtypes` and `date` filters
        to the search_terms dictionary."""

        if "TODOS" in sections:
            search_terms["pubname"] = ["DO1", "DO2", "DO3"]
        else:
            search_terms["pubname"] = self._parse_sections(sections)
        if department:
            search_terms["artcategory"] = department
        if department_ignore:
            search_terms["artcategory_ignore"] = department_ignore
        if pubtype:
            search_terms["arttype"] = pubtype
        publish_from = calculate_from_datetime(
            reference_date, SearchDate[search_date]
        ).strftime("%Y-%m-%d")
        publish_to = reference_date.strftime("%Y-%m-%d")
        search_terms["pubdate"] = [publish_from, publish_to]

        return search_terms

    @staticmethod
    def _split_sql_terms(terms: Dict) -> List:
        """Split SQL terms into a list, removing duplicates.
        Get only the values from the first key of the Dict."""
        
        first_key = next(iter(terms))
        return list(set(terms[first_key].values()))

    @staticmethod
    def _parse_sections(sections: List) -> List:
        """Parse DOU section codes into a list of section names based on
        SectionINLABS class. Avoid duplicates.

        Example:
            the section ["SECAO_1", "SECAO_3", "EDICAO_EXTRA_3D", "EDICAO_EXTRA",
            "EDICAO_EXTRA_1"] outputs ['DO1E', 'DO3E', 'DO1', 'DO3']
        """

        return list({SectionINLABS[section].value for section in sections})