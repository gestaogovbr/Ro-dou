"""Common use functions for manipulating dates and times.
"""

import os
from datetime import datetime

AIRFLOW_TIMEZONE = os.getenv("AIRFLOW__CORE__DEFAULT_TIMEZONE")

def remove_template_indentation(text: str) -> str:
    """Remove indentation in template strings.
    """

    return ''.join(line.strip() for line in text.splitlines())

def get_trigger_date(context: dict, local_time: bool = False) -> datetime:
    """ Calcula a data de disparo da execução da DAG.

        Caso seja uma execução agendada, será data_interval_end,
        que no Airflow é a data esperada em que a DAG seja executada
        (é igual a logical_date + o schedule).

        Caso seja feita ativação manual (trigger DAG), poderá ser
        passado o parâmetro trigger_date no JSON de configuração.
        Nesse caso, valerá esta. O parâmetro deve ser passado no
        formato ISO (ex.: 2021-01-02T12:00):

        {
            "trigger_date": "2021-01-02T12:00"
        }

        Caso seja feita a ativação manual (trigger DAG) sem passar
        esse parâmetro, será considerada a logical_date, que
        no caso é a data em que foi realizado o trigger (data atual).

        Caso o parâmetro local_time seja True, nos casos de execução
        agendada ou manual sem configuração será considerado o
        datetime convertido para o fuso horário setado para o
        ambiente do Airflow. Por padrão o parâmetro é False,
        considerando o horário UTC.
    """

    trigger_date_conf: str = (
        context["dag_run"].conf
        .get(
            "trigger_date", # trigger manual, especificando a variável
            None # ou com trigger manual, mas sem especificar variável
        )
    ) if context["dag_run"] and context["dag_run"].conf else None # execução agendada da dag+

    if context["dag_run"].external_trigger:
        if trigger_date_conf: # execução manual com configuração
            trigger_date: datetime = datetime.fromisoformat(trigger_date_conf)
        else: # execução manual sem configuração
            trigger_date: datetime = context["logical_date"]
            if local_time is True:
                trigger_date = trigger_date.in_timezone(AIRFLOW_TIMEZONE)

    else: # execução agendada
        trigger_date: datetime = context["data_interval_end"]
        if local_time is True:
            trigger_date = trigger_date.in_timezone(AIRFLOW_TIMEZONE)

    return trigger_date

base_template_trigger_date_local_time = '''
{% if dag_run.external_trigger is defined and dag_run.external_trigger %}
    {% if dag_run.conf is defined %}
        {% if dag_run.conf["trigger_date"] is defined %}
            {% set the_date = macros.datetime.fromisoformat(dag_run.conf["trigger_date"]) %}
        {% else %}
            {% set the_date = logical_date.in_timezone(\'''' + AIRFLOW_TIMEZONE + '''\')%}
        {% endif %}
    {% endif %}
{% else %}
    {% set the_date = data_interval_end.in_timezone(\'''' + AIRFLOW_TIMEZONE + '''\')%}
{% endif %}
'''

template_ano_mes_dia_trigger_local_time = remove_template_indentation(
    base_template_trigger_date_local_time +
    '{{ the_date.strftime("%d/%m/%Y") }}'
)
