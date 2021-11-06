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
from tempfile import NamedTemporaryFile
import textwrap
import markdown
import pandas as pd

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.python_operator import BranchPythonOperator
from airflow.providers.microsoft.mssql.hooks.mssql import MsSqlHook
from airflow.hooks.postgres_hook import PostgresHook
from airflow.hooks.base_hook import BaseHook
from airflow.operators.dummy_operator import DummyOperator
from airflow.utils.email import send_email

import sys
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from parsers import YAMLParser
from searchers import DOUSearcher

class DouDigestDagGenerator():
    """
    YAML based Generator of DAGs that digests the DOU (gazette) daily
    publication and send email report listing all documents matching
    pré-defined keywords. It's also possible to fetch keywords from the
    database.
    """

    SOURCE_DIR = os.path.join(os.environ['AIRFLOW_HOME'], 'dags/ro_dou/')
    YAMLS_DIR = os.path.join(SOURCE_DIR, 'dag_confs/')

    parser = YAMLParser
    searcher = DOUSearcher

    def __init__(self, on_retry_callback=None, on_failure_callback=None):
        self.searcher = DOUSearcher()
        self.on_retry_callback = on_retry_callback
        self.on_failure_callback = on_failure_callback



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
            'start_date': datetime(2021, 10, 18),
            'depends_on_past': False,
            'retries': 10,
            'retry_delay': timedelta(minutes=20),
            'on_retry_callback': self.on_retry_callback,
            'on_failure_callback': self.on_failure_callback,
        }
        dag = DAG(
            dag_id,
            default_args=default_args,
            schedule_interval=schedule,
            description=description,
            catchup=False,
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
                python_callable=self.searcher.exec_dou_search,
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
                    'report_date': '{{ next_ds }}',
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

    def send_report(self, search_report, subject, report_date,
                    email_to_list, attach_csv):
        """Builds the email content, the CSV if applies, and send it
        """
        full_subject = f"{subject} - DOU de {report_date}"

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

# Run dag generation
DouDigestDagGenerator().generate_dags()
