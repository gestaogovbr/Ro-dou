"""
Dynamic DAG generator integrated with YAML config system to create DAG
which searchs terms in the Gazzete [Diário Oficial da União-DOU] and
send it by email to the  provided `recipient_emails` list. The DAGs are
generated by YAML config files at `dag_confs` folder.

TODO:
[] - Possibilitar schedule_interval maior que 1 dia apenas
[] - Incluir opção para enviar CSV ou ODS junto
[] - Pseudo randomizar a definição do minuto exato que rodará para
     distribuir consumo
[] - Escrever README no repo
[] - Escrever tutorial no portal cginf
[] - Tratar casos de pesquisas com muitos resultados. Talvez enviar
     arquivo zipodo com resultados
[] - Set proper CONFIG_FILEPATH
"""

from datetime import date, datetime, timedelta
import os
import ast

import yaml

from airflow import DAG
from airflow.models import Variable
from airflow.operators.python_operator import PythonOperator
from airflow.hooks.mssql_hook import MsSqlHook
from airflow.utils.email import send_email

from FastETL.custom_functions.utils.encode_html import replace_to_html_encode
from FastETL.hooks.dou_hook import DOUHook, Section, SearchDate, Field
from airflow_commons.slack_messages import send_slack

CONFIG_FILEPATH = '/usr/local/airflow/dags/dou/dag_confs/'

def _exec_dou_search(term_list,
                     dou_sections: [str],
                     search_date,
                     field,
                     is_exact_search):
    dou_hook = DOUHook()

    sections = [Section[s] for s in dou_sections]
    all_results = {}
    for name in term_list:
        results = dou_hook.search_text(name,
                                       sections,
                                       SearchDate[search_date],
                                       Field[field],
                                       is_exact_search
                                       )
        if results:
            all_results[name] = {}
            all_results[name]['items'] = results

    return all_results

def _send_email_task(results, subject, email_to_list):
    """
    Envia e-mail de notificação dos aspectos mais relevantes do Diário
    Oficial da União edição Extra para o SIORG.
    """
    today_date = date.today().strftime("%d/%m/%Y")
    full_subject = f"{subject} - DOU de {today_date}"

    # Transforma a variavel string em um dicionario de dados
    results = ast.literal_eval(results)

    content = """
        <style>
            .resultado {
                border-bottom: 1px solid #707070;
                padding: 20px 0;
            }
            .search-total-label {
                font-size: 15px; margin: 0;
                padding: 0;
            }
            .secao-marker {
                color: #06acff;
                font-family: 'rawline',sans-serif;
                font-size: 18px;
                font-weight: bold;
                margin-bottom: 8px;
            }
            .title-marker {
                font-family: 'rawline',sans-serif;
                font-size: 20px;
                font-weight: bold;
                line-height: 26px;
                margin-bottom: 8px;
                margin-top: 0;
            }
            .title-marker a {
                color: #222;
                margin: 0;
                text-decoration: none;
                text-transform: uppercase;
            }
            .title-marker a:hover {
                text-decoration: underline;
            }
            .abstract-marker {
                font-size: 18px;
                font-weight: 500;
                line-height: 22px;
                max-height: 44px;
                margin-bottom: 5px;
                margin-top: 0;
                overflow: hidden;
            }
            .date-marker {
                color: #b1b1b1;
                font-family: 'rawline', sans-serif;
                font-size: 14px;
                font-weight: 500;
                margin-top: 0;
            }
        </style>
    """

    for result in results:
        content += f"""<div class='resultado'>
            <p class='search-total-label'>{len(results[result]['items'])} resultado"""
        content += (' ' if len(results[result]['items']) == 1 else 's ')
        content += f"""para <b>{result}</b></p>"""

        if len(results[result]['items']) > 0:
            for item in results[result]['items']:
                content += f"""<br>
                    <p class="secao-marker">{item['section']}</p>
                    <h5 class='title-marker'>
                    <a href='{item['href']}'>{item['title']}</a>
                    </h5>
                    <p class='abstract-marker'>{item['abstract']}</p>
                    <p class='date-marker'>{item['date']}</p>
                """
        content += "</div>"

    if results:
        send_email(to=email_to_list,
                   subject=full_subject,
                   html_content=replace_to_html_encode(content))

def _select_name_list(sql, conn_id):
    mssql_hook = MsSqlHook(mssql_conn_id=conn_id)
    names_df = mssql_hook.get_pandas_df(sql)
    first_column = names_df.iloc[:, 0]

    return first_column.tolist()

def create_dag(dag_id,
               dou_sections,
               search_date,
               search_field,
               is_exact_search,
               term_list,
               sql,
               conn_id,
               email_to_list,
               subject,
               schedule,
               description,
               tags):
    default_args = {
        'owner': 'yaml-gen-by-nitai',
        'start_date': datetime(2021, 6, 18),
        'depends_on_past': False,
        'retries': 5,
        'retry_delay': timedelta(minutes=20),
        'on_retry_callback': send_slack,
        'on_failure_callback': send_slack,
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
            select_name_list = PythonOperator(
                task_id='select_name_list',
                python_callable=_select_name_list,
                op_kwargs={
                    "sql": sql,
                    "conn_id": conn_id,
                    }
            )
            term_list = "{{ ti.xcom_pull(task_ids='select_name_list') }}"

        exec_dou_search = PythonOperator(
            task_id='exec_dou_search',
            python_callable=_exec_dou_search,
            op_kwargs={
                "term_list": term_list,
                "dou_sections": dou_sections,
                "search_date": search_date,
                "field": search_field,
                "is_exact_search": is_exact_search,
                }
        )
        if sql:
            select_name_list >> exec_dou_search

        send_email_task = PythonOperator(
            task_id='send_email_task',
            python_callable=_send_email_task,
            op_kwargs={
                "results": "{{ ti.xcom_pull(task_ids='exec_dou_search') }}",
                "subject": subject,
                "email_to_list": email_to_list,
                }
        )
        exec_dou_search >> send_email_task

    return dag

def parse_yaml_file(file_name):
    """Process the config file in order to instantiate the DAG in Airflow."""
    with open(CONFIG_FILEPATH + file_name, 'r') as file:
        dag_config_dict = yaml.safe_load(file)
        def try_get(variable: dict, field, error_msg=None):
            """Try to retrieve the property named as `field` from
            `variable` dict and raise apropriate message"""
            try:
                return variable[field]
            except KeyError:
                if not error_msg:
                    error_msg = f'O campo `{field}` é obrigatório.'
                error_msg = f'Erro no arquivo {file_name}: {error_msg}'

                raise ValueError(error_msg)

        dag = try_get(dag_config_dict, 'dag')
        dag_id = try_get(dag, 'id')
        description = try_get(dag, 'description')
        search = try_get(dag, 'search')
        report = try_get(dag, 'report')
        emails = try_get(report, 'emails')

        terms = try_get(search, 'terms')
        sql = None
        conn_id = None
        if isinstance(terms, dict):
            if 'from_airflow_variable' in terms:
                var_name = terms.get('from_airflow_variable')
                terms = ast.literal_eval(Variable.get(var_name))
            elif 'from_db_select' in terms:
                from_db_select = terms.get('from_db_select')
                sql = try_get(from_db_select, 'sql')
                conn_id = try_get(from_db_select, 'conn_id')
            else:
                raise ValueError('O campo `terms` aceita como valores válidos '
                                 'uma lista de strings ou parâmetros do tipo '
                                 '`from_airflow_variable` ou `from_db_select`.')

        # Optional fields
        subject = report.get('subject', 'Extraçao do DOU')
        dou_sections = search.get('dou_sections', ['TODOS'])
        search_date = search.get('date', 'DIA')
        field = search.get('field', 'TUDO')
        is_exact_search = search.get('is_exact_search', True)
        schedule = dag.get('schedule_interval', '@daily')
        tags = dag.get('tags', [])
        # add default tags
        tags.append('dou')
        tags.append('generated_dag')
        globals()[dag_id] = create_dag(
            dag_id,
            dou_sections,
            search_date,
            field,
            is_exact_search,
            terms,
            sql,
            conn_id,
            emails,
            subject,
            schedule,
            description,
            tags,
            )

yaml_files = [
    f for f in os.listdir(CONFIG_FILEPATH)
    if f.split('.')[-1] in ['yaml', 'yml']
]
for filename in yaml_files:
    parse_yaml_file(filename)
