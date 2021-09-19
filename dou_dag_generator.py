"""
Dynamic DAG generator with YAML config system to create DAG which
searchs terms in the Gazzete [Diário Oficial da União-DOU] and send it
by email to the  provided `recipient_emails` list. The DAGs are
generated by YAML config files at `dag_confs` folder.

TODO:
[] - Definir sufixo do título do email a partir de configuração
"""

from datetime import date, datetime, timedelta
import os
import ast
import time
import re
from random import random
from tempfile import NamedTemporaryFile
import textwrap
import markdown
import pandas as pd

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.python_operator import BranchPythonOperator
from airflow.providers.microsoft.mssql.hooks.mssql import MsSqlHook
from airflow.operators.dummy_operator import DummyOperator
from airflow.utils.email import send_email

from unidecode import unidecode

from FastETL.hooks.dou_hook import DOUHook, Section, SearchDate, Field

from airflow_commons.slack_messages import send_slack
from airflow_commons.utils.date import get_trigger_date

import sys
sys.path.insert(0,os.path.abspath(os.path.dirname(__file__)))
from parsers import YAMLParser

class DouDigestDagGenerator():
    """
    YAML based Generator of DAGs that digests the DOU (gazette) daily
    publication and send email report listing all documents matching
    pré-defined keywords. It's also possible to fetch keywords from the
    database.
    """

    SOURCE_DIR = os.path.join(os.environ['AIRFLOW_HOME'], 'dags/ro-dou/')
    YAMLS_DIR = os.path.join(SOURCE_DIR, 'dag_confs/')
    SCRAPPING_INTERVAL = 2
    CLEAN_HTML_RE = re.compile('<.*?>')
    SPLIT_MATCH_RE = re.compile(r'(.*?)<.*?>(.*?)<.*?>')

    parser = YAMLParser

    def generate_dags(self):
        """Iterates over the YAML files and creates all dags
        """
        files_list = [
            f for f in os.listdir(self.YAMLS_DIR)
            if f.split('.')[-1] in ['yaml', 'yml']
        ]

        for file in files_list:
            dag_specs = self.parser(
                filepath=os.path.join(self.YAMLS_DIR, file)).parse()
            dag_id = dag_specs[0]
            globals()[dag_id] = self.create_dag(*dag_specs)

    def create_dag(self,
                   dag_id,
                   dou_sections,
                   search_date,
                   search_field,
                   is_exact_search,
                   ignore_signature_match,
                   force_rematch,
                   term_list,
                   sql,
                   conn_id,
                   email_to_list,
                   subject,
                   attach_csv,
                   schedule,
                   description,
                   tags):
        """Creates the DAG object and tasks

        Depending on configuration it adds an extra prior task to query
        the term_list from a database
        """
        default_args = {
            'owner': 'nitai',
            'start_date': datetime(2021, 6, 18),
            'depends_on_past': False,
            'retries': 10,
            'retry_delay': timedelta(minutes=20),
            'on_retry_callback': send_slack,
            'on_failure_callback': send_slack,
        }
        dag = DAG(
            dag_id,
            default_args=default_args,
            schedule_interval=schedule,
            description=description,
            catchup=True,
            tags=tags
            )

        with dag:
            if sql:
                select_terms_from_db_task = PythonOperator(
                    task_id='select_terms_from_db',
                    python_callable=self.select_terms_from_db,
                    op_kwargs={
                        'sql': sql,
                        'conn_id': conn_id,
                        }
                )
                term_list = "{{ ti.xcom_pull(task_ids='select_terms_from_db') }}"

            exec_dou_search_task = PythonOperator(
                task_id='exec_dou_search',
                python_callable=self.exec_dou_search,
                op_kwargs={
                    'term_list': term_list,
                    'dou_sections': dou_sections,
                    'search_date': search_date,
                    'field': search_field,
                    'is_exact_search': is_exact_search,
                    'ignore_signature_match': ignore_signature_match,
                    'force_rematch': force_rematch,
                    },
            )
            if sql:
                select_terms_from_db_task >> exec_dou_search_task # pylint: disable=pointless-statement

            has_matches_task = BranchPythonOperator(
                task_id='has_matches',
                python_callable=self.has_matches,
                op_kwargs={
                    'search_result': "{{ ti.xcom_pull(task_ids='exec_dou_search') }}",
                },
            )

            skip_report_task = DummyOperator(task_id='skip_report')

            send_report_task = PythonOperator(
                task_id='send_report',
                python_callable=self.send_report,
                op_kwargs={
                    'search_report': "{{ ti.xcom_pull(task_ids='exec_dou_search') }}",
                    'subject': subject,
                    'email_to_list': email_to_list,
                    'attach_csv': attach_csv,
                    },
            )
            exec_dou_search_task >> has_matches_task # pylint: disable=pointless-statement
            has_matches_task >> [send_report_task, skip_report_task]

        return dag

    def has_matches(self, search_result: str) -> str:
        search_result = ast.literal_eval(search_result)
        items = ['contains' for k, v in search_result.items() if v]

        return 'send_report' if items else 'skip_report'

    def select_terms_from_db(self, sql: str, conn_id: str):
        """Queries the `sql` and return the list of terms that will be
        used later in the DOU search. The first column of the select
        must contain the terms to be searched. The second column, which
        is optional, is a classifier that will be used to group and sort
        the email report and the generated CSV.
        """
        mssql_hook = MsSqlHook(mssql_conn_id=conn_id)
        terms_df = mssql_hook.get_pandas_df(sql)
        # Remove unnecessary spaces and change null for ''
        terms_df = terms_df.applymap(
            lambda x: str.strip(x) if pd.notnull(x) else '')

        return terms_df.to_json(orient="columns")

    def send_report(self, search_report, subject, email_to_list,
                         attach_csv):
        """Builds the email content, the CSV if applies, and send it
        """
        today_date = date.today().strftime("%d/%m/%Y")
        full_subject = f"{subject} - DOU de {today_date}"

        search_report = ast.literal_eval(search_report)
        content = self.generate_email_content(search_report)

        if attach_csv:
            with self.get_csv_tempfile(search_report) as csv_file:
                send_email(
                    to=email_to_list,
                    subject=full_subject,
                    files=[csv_file.name],
                    html_content=content,
                    mime_charset='utf-8')
        else:
            send_email(
                to=email_to_list,
                subject=full_subject,
                html_content=content,
                mime_charset='utf-8')

    def generate_email_content(self, search_report: dict) -> str:
        """Generate HTML content to be sent by email based on
        search_report dictionary
        """
        with open(os.path.join(self.SOURCE_DIR, 'report_style.css'), 'r') as f:
            blocks = [f'<style>\n{f.read()}</style>']

        for group, results in search_report.items():
            if group != 'single_group':
                blocks.append('\n')
                blocks.append(f'**Grupo: {group}**')
                blocks.append('\n\n')

            for term, items in results.items():
                blocks.append('\n')
                blocks.append(f'* # Resultados para: {term}')

                for item in items:
                    sec_desc = DOUHook.SEC_DESCRIPTION[item['section']]
                    item_html = f"""
                        <p class="secao-marker">{sec_desc}</p>
                        ### [{item['title']}]({item['href']})
                        <p class='abstract-marker'>{item['abstract']}</p>
                        <p class='date-marker'>{item['date']}</p>"""
                    blocks.append(
                        textwrap.indent(textwrap.dedent(item_html), ' ' * 4))
                blocks.append('---')
            blocks.append('---')

        return markdown.markdown('\n'.join(blocks))

    def get_csv_tempfile(self, search_report: dict) -> NamedTemporaryFile:
        temp_file = NamedTemporaryFile(prefix='extracao_dou_', suffix='.csv')
        self.convert_report_to_dataframe(search_report)\
            .to_csv(temp_file, index=False)
        return temp_file

    def convert_report_to_dataframe(self, search_report: dict) -> pd.DataFrame:
        df = pd.DataFrame(self.convert_report_dict_to_tuple_list(search_report))
        df.columns = ['Grupo', 'Termo de pesquisa', 'Seção', 'URL',
                      'Título', 'Resumo', 'Data']
        if 'single_group' in search_report:
            del df['Grupo']
        return df

    def convert_report_dict_to_tuple_list(self, search_report: dict) -> list:
        tuple_list = []
        for group, results in search_report.items():
            for term, matchs in results.items():
                for match in matchs:
                    tuple_list.append(
                        self.repack_match(group, term, match))
        return tuple_list

    def repack_match(self,
                     group: str,
                     search_term: str,
                     match: dict) -> tuple:
        return (group,
                search_term,
                DOUHook.SEC_DESCRIPTION[match['section']],
                match['href'],
                match['title'],
                match['abstract'],
                match['date'],
                )

    def exec_dou_search(self,
                         term_list,
                         dou_sections: [str],
                         search_date,
                         field,
                         is_exact_search: bool,
                         ignore_signature_match: bool,
                         force_rematch: bool,
                         **context):
        search_results = self.search_all_terms(self.cast_term_list(term_list),
                                               dou_sections,
                                               search_date,
                                               get_trigger_date(context),
                                               field,
                                               is_exact_search,
                                               ignore_signature_match,
                                               force_rematch)
        print(search_results)
        return self.group_results(search_results, term_list)

    def group_results(self,
                      search_results: dict,
                      term_list: [list, str]) -> dict:
        """Produces a grouped result based on if `term_list` is already
        the list of terms or it is a string received through xcom
        from `select_terms_from_db` task and the sql_query returned a
        second column (used as the group name)
        """
        if isinstance(term_list, str) \
            and len(ast.literal_eval(term_list).values()) > 1:
            grouped_result = self.group_by_term_group(search_results, term_list)
        else:
            grouped_result = {'single_group': search_results}

        return grouped_result

    def group_by_term_group(self,
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

    def cast_term_list(self, pre_term_list: [list, str]) -> list:
        """If `pre_term_list` is a str (in the case it came from xcom)
        then its necessary to convert it back to dataframe and return
        the first column. Otherwise the `pre_term_list` is returned.
        """
        return pre_term_list if isinstance(pre_term_list, list) else \
            pd.read_json(pre_term_list).iloc[:, 0].tolist()

    def search_all_terms(self,
                         term_list,
                         dou_sections,
                         search_date,
                         trigger_date,
                         field,
                         is_exact_search,
                         ignore_signature_match,
                         force_rematch) -> dict:
        search_results = {}
        dou_hook = DOUHook()
        for search_term in term_list:
            results = dou_hook.search_text(
                search_term=search_term,
                sections=[Section[s] for s in dou_sections],
                reference_date=trigger_date,
                search_date=SearchDate[search_date],
                field=Field[field],
                is_exact_search=is_exact_search
                )
            if ignore_signature_match:
                results = [r for r in results
                           if not self.is_signature(search_term,
                                                    r.get('abstract'))]
            if force_rematch:
                results = [r for r in results
                           if self.really_matched(search_term,
                                                  r.get('abstract'))]

            if results:
                search_results[search_term] = results

            time.sleep(self.SCRAPPING_INTERVAL * random() * 2)

        return search_results

    def really_matched(self, search_term: str, abstract: str) -> bool:
        """Verifica se o termo encontrado pela API realmente é igual ao
        termo de busca. Esta função é útil para filtrar resultados
        retornardos pela API mas que são resultados aproximados e não
        exatos.
        """
        whole_match = self.clean_html(abstract).replace('... ', '')
        norm_whole_match = self.normalize(whole_match)

        norm_term = self.normalize(search_term)

        return norm_term in norm_whole_match

    def is_signature(self, search_term: str, abstract: str) -> bool:
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
        clean_abstract = self.clean_html(abstract)
        start_name, match_name = self.get_prior_and_matched_name(abstract)

        norm_abstract = self.normalize(clean_abstract)
        norm_abstract_withou_start_name = norm_abstract[len(start_name):]
        norm_term = self.normalize(search_term)

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

    def normalize(self, raw_str: str) -> str:
        """Remove characters (accents and other not alphanumeric) lower
        it and keep only one space between words"""
        text = unidecode(raw_str).lower()
        text = ''.join(c if c.isalnum() else ' ' for c in text)
        text = ' '.join(text.split())
        return text

    def get_prior_and_matched_name(self, raw_html: str) -> (str, str):
        groups = self.SPLIT_MATCH_RE.match(raw_html).groups()
        return groups[0], groups[1]

    def clean_html(self, raw_html: str) -> str:
        clean_text = re.sub(self.CLEAN_HTML_RE, '', raw_html)
        return clean_text

# Run dag generation
DouDigestDagGenerator().generate_dags()
