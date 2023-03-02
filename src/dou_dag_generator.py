"""
Dynamic DAG generator with YAML config system to create DAG which
searchs terms in the Gazzete [Diário Oficial da União-DOU] and send it
by email to the  provided `recipient_emails` list. The DAGs are
generated by YAML config files at `dag_confs` folder.

TODO:
[] - Definir sufixo do título do email a partir de configuração
"""

from datetime import datetime, timedelta
import os
import ast
from dataclasses import asdict
from tempfile import NamedTemporaryFile
import textwrap
from typing import Dict, List
import logging
import markdown
import pandas as pd

from airflow import DAG
from airflow.operators.python import PythonOperator, BranchPythonOperator
from airflow.providers.microsoft.mssql.hooks.mssql import MsSqlHook
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.hooks.base import BaseHook
from airflow.operators.empty import EmptyOperator
from airflow.utils.email import send_email
from FastETL.custom_functions.utils.date import template_ano_mes_dia_trigger_local_time
from FastETL.custom_functions.utils.date import get_trigger_date

import sys
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from parsers import YAMLParser, DAGConfig
from searchers import BaseSearcher, DOUSearcher, QDSearcher

class DouDigestDagGenerator():
    """
    YAML based Generator of DAGs that digests the DOU (gazette) daily
    publication and send email report listing all documents matching
    pré-defined keywords. It's also possible to fetch keywords from the
    database.
    """

    base_dir = os.path.join(os.environ['AIRFLOW_HOME'], 'dags')
    dir_name = 'ro_dou'

    # Walk through the directory tree to find the directory
    for root, dirs, files in os.walk(base_dir):
        if dir_name in dirs:
            # If the directory is found, print its path and exit the loop
            SOURCE_DIR = os.path.join(root, dir_name)
            break
    else:
        # If the directory is not found, print a message
        raise Exception("{dir_name} directory not found in {base_dir} or its subdirectories.")

    YAMLS_DIR = os.path.join(SOURCE_DIR, 'dag_confs')

    parser = YAMLParser
    searchers: Dict[str, BaseSearcher]

    def __init__(self, on_retry_callback=None, on_failure_callback=None):
        self.searchers = {
            'DOU': DOUSearcher(),
            'QD': QDSearcher(),
        }
        self.on_retry_callback = on_retry_callback
        self.on_failure_callback = on_failure_callback

    @staticmethod
    def prepare_doc_md(specs: DAGConfig, config_file: str) -> str:
        """Prepares the markdown documentation for a dag.

        Args:
            specs (DAGConfig): A DAG configuration object.
            config_file (str): The name of a DAG config file.

        Returns:
            str: The DAG documentation in markdown format.
        """
        config = asdict(specs)
        # options that won't show in the "DAG Docs"
        del config["description"]
        del config["doc_md"]
        doc_md = (
            specs.doc_md +
            textwrap.dedent(f"""

            **Configuração da dag definida no arquivo `{config_file}`**:

            <dl>
            """
            )
        )
        for key, value in config.items():
            doc_md = doc_md + f"<dt>{key}</dt>"
            if isinstance(value, list) or isinstance(value, set):
                doc_md = doc_md + (
                    "<dd>\n\n" +
                    " * " +
                    "\n * ".join(str(item) for item in value) +
                    "\n</dd>"
                )
            else:
                doc_md = doc_md + f"<dd>{str(value)}</dd>"
            doc_md = doc_md + "\n"
        doc_md = doc_md + "</dl>\n"
        return doc_md

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
            dag_id = dag_specs.dag_id
            globals()[dag_id] = self.create_dag(dag_specs, file)

    def create_dag(self, specs: DAGConfig, config_file: str) -> DAG:
        """Creates the DAG object and tasks

        Depending on configuration it adds an extra prior task to query
        the term_list from a database
        """
        # Prepare the markdown documentation
        doc_md = self.prepare_doc_md(
            specs, config_file) if specs.doc_md else specs.doc_md
        # DAG parameters
        default_args = {
            'owner': 'nitai',
            'start_date': datetime(2021, 10, 18),
            'depends_on_past': False,
            'retries': 10,
            'retry_delay': timedelta(minutes=20),
            'on_retry_callback': self.on_retry_callback,
            'on_failure_callback': self.on_failure_callback,
        }
        dag = DAG(
            specs.dag_id,
            default_args=default_args,
            schedule=specs.schedule,
            description=specs.description,
            doc_md=doc_md,
            catchup=False,
            params={
                "trigger_date": "2022-01-02T12:00"
            },
            tags=specs.dag_tags
            )

        with dag:
            if specs.sql:
                select_terms_from_db_task = PythonOperator(
                    task_id='select_terms_from_db',
                    python_callable=self.select_terms_from_db,
                    op_kwargs={
                        'sql': specs.sql,
                        'conn_id': specs.conn_id,
                        }
                )
                term_list = "{{ ti.xcom_pull(task_ids='select_terms_from_db') }}"

            exec_dou_search_task = PythonOperator(
                task_id='exec_dou_search',
                python_callable=self.perform_searches,
                op_kwargs={
                    'sources': specs.sources,
                    'territory_id': specs.territory_id,
                    'term_list': specs.terms or term_list,
                    'dou_sections': specs.dou_sections,
                    'search_date': specs.search_date,
                    'field': specs.field,
                    'is_exact_search': specs.is_exact_search,
                    'ignore_signature_match': specs.ignore_signature_match,
                    'force_rematch': specs.force_rematch,
                    },
            )
            if specs.sql:
                select_terms_from_db_task >> exec_dou_search_task # pylint: disable=pointless-statement

            has_matches_task = BranchPythonOperator(
                task_id='has_matches',
                python_callable=self.has_matches,
                op_kwargs={
                    'search_result': "{{ ti.xcom_pull(task_ids='exec_dou_search') }}",
                    'skip_null': specs.skip_null,
                },
            )

            skip_report_task = EmptyOperator(task_id='skip_report')

            send_report_task = PythonOperator(
                task_id='send_report',
                python_callable=self.send_report,
                op_kwargs={
                    'search_report_str': "{{ ti.xcom_pull(task_ids='exec_dou_search') }}",
                    'subject': specs.subject,
                    'report_date': template_ano_mes_dia_trigger_local_time,
                    'email_to_list': specs.emails,
                    'attach_csv': specs.attach_csv,
                    'skip_null': specs.skip_null,
                    },
            )
            exec_dou_search_task >> has_matches_task # pylint: disable=pointless-statement
            has_matches_task >> [send_report_task, skip_report_task]

        return dag


    def perform_searches(
        self,
        sources,
        territory_id,
        term_list,
        dou_sections: [str],
        search_date,
        field,
        is_exact_search: bool,
        ignore_signature_match: bool,
        force_rematch: bool,
        **context) -> dict:
        """Performs the search in each source and merge the results
        """
        logging.info('Searching for the following terms: %s', ','.join(term_list))
        logging.info('Trigger date: ' + str(get_trigger_date(context, local_time = True)))
        if 'DOU' in sources:
            dou_result = self.searchers['DOU'].exec_search(
                term_list,
                dou_sections,
                search_date,
                field,
                is_exact_search,
                ignore_signature_match,
                force_rematch,
                get_trigger_date(context, local_time = True))

        if 'QD' in sources:
            qd_result = self.searchers['QD'].exec_search(
                territory_id,
                term_list,
                dou_sections,
                search_date,
                field,
                is_exact_search,
                ignore_signature_match,
                force_rematch,
                get_trigger_date(context, local_time = True))

        if 'DOU' in sources and 'QD' in sources:
            return merge_results(qd_result, dou_result)
        elif 'DOU' in sources:
            return dou_result
        else:
            return qd_result


    def has_matches(self, search_result: str, skip_null: bool) -> str:
        if skip_null:
            search_result = ast.literal_eval(search_result)
            items = ['contains' for k, v in search_result.items() if v]
            return 'send_report' if items else 'skip_report'
        else:
            return 'send_report'

    def select_terms_from_db(self, sql: str, conn_id: str):
        """Queries the `sql` and return the list of terms that will be
        used later in the DOU search. The first column of the select
        must contain the terms to be searched. The second column, which
        is optional, is a classifier that will be used to group and sort
        the email report and the generated CSV.
        """
        conn_type = BaseHook.get_connection(conn_id).conn_type
        if conn_type == 'mssql':
            db_hook = MsSqlHook(conn_id)
        elif conn_type in ('postgresql', 'postgres'):
            db_hook = PostgresHook(conn_id)
        else:
            raise Exception('Tipo de banco de dados não suportado: ', conn_type)

        terms_df = db_hook.get_pandas_df(sql)
        # Remove unnecessary spaces and change null for ''
        terms_df = terms_df.applymap(
            lambda x: str.strip(x) if pd.notnull(x) else '')

        return terms_df.to_json(orient="columns")

    def send_report(self, search_report_str: str, subject, report_date,
                    email_to_list, attach_csv, skip_null):
        """Builds the email content, the CSV if applies, and send it
        """
        full_subject = f"{subject} - DOs de {report_date}"
        search_report = ast.literal_eval(search_report_str)
        items = ['contains' for k, v in search_report.items() if v]
        if items:
            content = self.generate_email_content(search_report)
        else:
            if skip_null:
                return 'skip_report'
            content = "Nenhum dos termos pesquisados foi encontrado."

        if attach_csv and items:
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
                    sec_desc = item['section']
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
                match['section'],
                match['href'],
                match['title'],
                match['abstract'],
                match['date'],
                )


def _merge_dict(dict1, dict2):
    """Merge dictionaries and sum values of common keys"""
    dict3 = {**dict1, **dict2}
    for key, value in dict3.items():
        if key in dict1 and key in dict2:
                dict3[key] = value + dict1[key]
    return dict3


SearchResult = Dict[str, Dict[str, List[dict]]]

def merge_results(result_1: SearchResult,
                  result_2: SearchResult) -> SearchResult:
    """Merge search results by group and term as keys"""
    return {
        group: _merge_dict(result_1.get(group, {}),
                           result_2.get(group, {}))
        for group in set((*result_1, *result_2))}


# Run dag generation
DouDigestDagGenerator().generate_dags()
