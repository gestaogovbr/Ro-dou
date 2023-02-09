"""Abstract and concrete classes to perform terms searchs.
"""

import ast
import json
import logging
import re
import time
from abc import ABC
from datetime import datetime, timedelta
from random import random
from typing import Dict, List, Tuple
from urllib.parse import urljoin

import pandas as pd
import requests
from FastETL.hooks.dou_hook import DOUHook, Field, SearchDate, Section
from unidecode import unidecode


class BaseSearcher(ABC):
    SCRAPPING_INTERVAL = 1
    CLEAN_HTML_RE = re.compile('<.*?>')


    def _cast_term_list(self, pre_term_list: Dict[list, str]) -> list:
        """If `pre_term_list` is a str (in the case it came from xcom)
        then its necessary to convert it back to dataframe and return
        the first column. Otherwise the `pre_term_list` is returned.
        """
        return pre_term_list if isinstance(pre_term_list, list) else \
            pd.read_json(pre_term_list).iloc[:, 0].tolist()


    def _group_results(self,
                       search_results: dict,
                       term_list: Dict[list, str]) -> dict:
        """Produces a grouped result based on if `term_list` is already
        the list of terms or it is a string received through xcom
        from `select_terms_from_db` task and the sql_query returned a
        second column (used as the group name)
        """
        if isinstance(term_list, str) \
            and len(ast.literal_eval(term_list).values()) > 1:
            grouped_result = self._group_by_term_group(search_results, term_list)
        else:
            grouped_result = {'single_group': search_results}

        return grouped_result


    def _group_by_term_group(self,
                            search_results: dict,
                            term_n_group: str) -> dict:
        """Rebuild the dict grouping the results based on term_n_group
        mapping
        """
        dict_struct = ast.literal_eval(term_n_group)
        terms, groups = dict_struct.values()
        term_group_map = dict(zip(terms.values(), groups.values()))
        groups = sorted(list(set(term_group_map.values())))

        grouped_result = {
            g1:{
                t: search_results[t]
                for (t, g2) in sorted(term_group_map.items())
                if t in search_results and g1 == g2}
            for g1 in groups}

        # Clear empty groups
        trimmed_result = {k: v for k, v in grouped_result.items() if v}
        return trimmed_result


    def _really_matched(self, search_term: str, abstract: str) -> bool:
        """Verifica se o termo encontrado pela API realmente é igual ao
        termo de busca. Esta função é útil para filtrar resultados
        retornardos pela API mas que são resultados aproximados e não
        exatos.
        """
        whole_match = self._clean_html(abstract).replace('... ', '')
        norm_whole_match = self._normalize(whole_match)

        norm_term = self._normalize(search_term)

        return norm_term in norm_whole_match


    def _clean_html(self, raw_html: str) -> str:
        clean_text = re.sub(self.CLEAN_HTML_RE, '', raw_html)
        return clean_text


    def _normalize(self, raw_str: str) -> str:
        """Remove characters (accents and other not alphanumeric) lower
        it and keep only one space between words"""
        text = unidecode(raw_str).lower()
        text = ''.join(c if c.isalnum() else ' ' for c in text)
        text = ' '.join(text.split())
        return text


class DOUSearcher(BaseSearcher):
    SPLIT_MATCH_RE = re.compile(r'(.*?)<.*?>(.*?)<.*?>')
    dou_hook = DOUHook()

    def exec_search(self,
                    term_list,
                    dou_sections: List[str],
                    search_date,
                    field,
                    is_exact_search: bool,
                    ignore_signature_match: bool,
                    force_rematch: bool,
                    reference_date: datetime):
        search_results = self._search_all_terms(
            self._cast_term_list(term_list),
            dou_sections,
            search_date,
            reference_date,
            field,
            is_exact_search,
            ignore_signature_match,
            force_rematch)

        return self._group_results(search_results, term_list)

    def _search_all_terms(self,
                          term_list,
                          dou_sections,
                          search_date,
                          trigger_date,
                          field,
                          is_exact_search,
                          ignore_signature_match,
                          force_rematch) -> dict:
        search_results = {}
        for search_term in term_list:
            logging.info('Starting search for term: %s', search_term)
            results = self._search_text_with_retry(
                search_term=search_term,
                sections=[Section[s] for s in dou_sections],
                reference_date=trigger_date,
                search_date=SearchDate[search_date],
                field=Field[field],
                is_exact_search=is_exact_search
                )
            if ignore_signature_match:
                results = [r for r in results
                           if not self._is_signature(search_term,
                                                     r.get('abstract'))]
            if force_rematch:
                results = [r for r in results
                           if self._really_matched(search_term,
                                                   r.get('abstract'))]

            results = self._render_section_descriptions(results)

            if results:
                search_results[search_term] = results

            time.sleep(self.SCRAPPING_INTERVAL * random() * 2)

        return search_results

    def _search_text_with_retry(
        self,
        search_term,
        sections,
        reference_date,
        search_date,
        field,
        is_exact_search,
        max_retries=5
    ) -> list:

        retry=1

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
                if retry > max_retries:
                    logging.error('Error - Max retries reached')
                    raise Exception
                logging.info('Attemp %s of %s: ', retry, max_retries)
                logging.info('Sleeping for 30 seconds before retry dou_hook.search_text().')
                time.sleep(30)
                retry += 1

    def _is_signature(self, search_term: str, abstract: str) -> bool:
        """Verifica se o `search_term` (geralmente usado para busca por
        nome de pessoas) está presente na assinatura. Para isso se
        utiliza de um "bug" da API que, para estes casos, retorna o
        `abstract` iniciando com a assinatura do documento, o que não
        ocorre quando o match acontece em outras partes do documento.
        Dessa forma esta função checa se isso ocorreu e é utilizada para
        filtrar os resultados presentes no relatório final. Também
        resolve os casos em que o nome da pessoa é parte de nome maior.
        Por exemplo o nome 'ANTONIO DE OLIVEIRA' é parte do nome 'JOSÉ
        ANTONIO DE OLIVEIRA MATOS'
        """
        clean_abstract = self._clean_html(abstract)
        start_name, match_name = self._get_prior_and_matched_name(abstract)

        norm_abstract = self._normalize(clean_abstract)
        norm_abstract_withou_start_name = norm_abstract[len(start_name):]
        norm_term = self._normalize(search_term)

        return (
            # Considera assinatura apenas se aparecem com uppercase
            (start_name + match_name).isupper() and
                # Resolve os casos '`ANTONIO DE OLIVEIRA`' e
                # '`ANTONIO DE OLIVEIRA` MATOS'
                (norm_abstract.startswith(norm_term) or
                # Resolve os casos 'JOSÉ `ANTONIO DE OLIVEIRA`' e
                # ' JOSÉ `ANTONIO DE OLIVEIRA` MATOS'
                norm_abstract_withou_start_name.startswith(norm_term))
        )

    def _get_prior_and_matched_name(self, raw_html: str) -> Tuple[str, str]:
        groups = self.SPLIT_MATCH_RE.match(raw_html).groups()
        return groups[0], groups[1]

    def _render_section_descriptions(self, results: list) -> list:
        return [self._render_section(r) for r in results]

    def _render_section(self, result: dict) -> dict:
        result['section'] = f"DOU - {DOUHook.SEC_DESCRIPTION[result['section']]}"
        return result


class QDSearcher(BaseSearcher):

    API_BASE_URL = 'https://queridodiario.ok.org.br/api/gazettes'
    def exec_search(self,
                    territory_id,
                    term_list,
                    dou_sections: List[str],
                    search_date,
                    field,
                    is_exact_search: bool,
                    ignore_signature_match: bool,
                    force_rematch: bool,
                    reference_date: datetime):
        force_rematch = True if force_rematch is None else force_rematch
        term_list = self._cast_term_list(term_list)
        tailored_date = reference_date - timedelta(days=1)
        search_results = {}
        for search_term in term_list:
            results = self._search_term(
                territory_id=territory_id,
                search_term=search_term,
                reference_date=tailored_date,
                force_rematch=force_rematch,
                )
            if results:
                search_results[search_term] = results
            time.sleep(self.SCRAPPING_INTERVAL * random() * 2)

        return self._group_results(search_results, term_list)


    def _search_term(self,
                     territory_id,
                     search_term,
                     reference_date,
                     force_rematch: bool,
                     ) -> list:
        payload = [
            ('size', 100),
            ('excerpt_size', 250),
            ('sort_by', 'descending_date'),
            ('pre_tags', ('<span style="font-family: \'rawline\','
                          'sans-serif; background: #FFA;">')),
            ('post_tags', '</span>'),
            ('number_of_excerpts', 3),
            ('published_since', reference_date.strftime('%Y-%m-%d')),
            ('published_until', reference_date.strftime('%Y-%m-%d')),
            ('querystring', f'"{search_term}"')]

        if territory_id:
            payload.append(('territory_ids', territory_id))

        req_result = requests.get(self.API_BASE_URL, params=payload)

        parsed_results = [
            self.parse_result(result)
            for result in json.loads(req_result.content)['gazettes']]

        return parsed_results


    def parse_result(self, result: dict, result_as_email: bool=True) -> dict:
        section = ('extraordinária'
            if result.get('is_extra_edition', False) else 'ordinária')
        if result_as_email:
            abstract = (
                '<p>'
                + '</p><p>'.join(result['excerpts']).replace('\n', '')
                + '</p>')
        else:
            abstract = '\n'.join(result['excerpts']).replace('\n', '')
        return {
            'section': f"QD - Edição {section} ",
            'title': ("Município de "
                f"{result['territory_name']} - {result['state_code']}"),
            'href': result['url'],
            'abstract': abstract,
            'date': result['date'],
        }
