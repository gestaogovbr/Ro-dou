"""Common use functions for manipulating dates and times.
"""

import os
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta

AIRFLOW_TIMEZONE = os.getenv("AIRFLOW__CORE__DEFAULT_TIMEZONE")

def remove_template_indentation(text: str) -> str:
    """Remove indentation in template strings.
    """

    return ''.join(line.strip() for line in text.splitlines())

def get_reference_date(context: dict) -> datetime:
    """Calculates the reference date of the DAG execution.

    If it is a scheduled execution, it will be the logical_date, which
    in Airflow is the start date of the execution interval for the DAG.

    If it is triggered manually (trigger DAG), the reference_date
    parameter can be passed in the configuration JSON. In this case,
    it will be used instead of logical_date. The parameter must be
    passed in ISO format (e.g., 2021-01-02T12:00):

    {
        "reference_date": "2021-01-02T12:00"
    }

    If manual activation (trigger DAG) is done without passing this
    parameter, an exception will be raised.

    Args:
        context (dict): Airflow information about current task.

    Raises:
        ValueError: Manual trigger without reference_date parameter

    Returns:
        datetime: reference date based on how dag was triggered
    """

    # trigger manual, without variable reference_date defined
    if context["dag_run"].external_trigger and \
        context["dag_run"].conf is not None and \
        "reference_date" not in context["dag_run"].conf:
        raise ValueError(
            'Para executar esta DAG manualmente é necessário incluir o '
            'parâmetro reference_date no JSON das configurações.')

    reference_date: datetime = (
        datetime.fromisoformat(
            context["dag_run"].conf["reference_date"]
        )
    ) if context["dag_run"].conf \
        else context["logical_date"] # dag run scheduled

    return reference_date

def get_trigger_date(context: dict, local_time: bool = False) -> datetime:
    """ Calculate the start date of the DAG execution.

        If the execution is a scheduled execution,
        the data_interval_end will be activated.In Airflow,
        this represents the predetermined date when the DAG is executed.
        (It is equivalent to the logical_date plus the schedule interval).

        If the manual activation is performed (triggering the DAG),
        the parameter trigger_date can be activated in the JSON configurations.
        In this approach, the parameter must be provided in ISO
        format (ex.: 2021-01-02T12:00):

        {
            "trigger_date": "2021-01-02T12:00"
        }

        If manual activation has been performed (triggering the DAG)
        and the parameter is not provided, the trigger will be identified
        as a logical_date. In this case, the date will be
        the current date and time when the trigger is executed (actualy date).

        If the local_time parameter is set to True, in both scheduled and manual
        executions where the configurations are not specified,
        the datetime can be converted to the timezone set in Airflow.
        By default, the local_time parameter is set to False,
        and the analysis is performed using the UTC timezone.
    """

    trigger_date_conf: str = (
        context["dag_run"].conf
        .get(
            "trigger_date", # Either a manual trigger with the variable specified,
            None # or a manual trigger where the variable is not specified.
        )
    ) if context["dag_run"] and context["dag_run"].conf else None # This is a scheduled execution of the dag+

    if context["dag_run"].external_trigger:
        if trigger_date_conf: # manual execution with configuration specified
            trigger_date: datetime = datetime.fromisoformat(trigger_date_conf)
        else: # manual execution without configuration specified
            trigger_date: datetime = context["logical_date"]
            if local_time is True:
                trigger_date = trigger_date.in_timezone(AIRFLOW_TIMEZONE)

    else: # scheduled execution
        trigger_date: datetime = context["data_interval_end"]
        if local_time is True:
            trigger_date = trigger_date.in_timezone(AIRFLOW_TIMEZONE)

    return trigger_date

def last_day_of_month(the_date: date):
    """ Returns the final day of the current month.
    """
    # obs.: timedelta does not support months as an argument; it returns values based on days.
    return (
        the_date + relativedelta(months=+1)
    ).replace(day=1) - timedelta(days=1)

def last_day_of_last_month(the_date: date):
    """ Returns the final day of the month preceding the current one.
    """
    return the_date.replace(day=1) - timedelta(days=1)

# Uses the same logic as "get_reference_date" to calculate the DAG's execution start date.

# used to complete the following templates, don't use in dags!
base_template_reference_date = '''
{% if dag_run.conf["reference_date"] is defined %}
    {% set the_date = macros.datetime.fromisoformat(dag_run.conf["reference_date"]) %}
{% else %}
    {% if dag_run.external_trigger %}
        {{ raise_exception_fazer_trigger_dag_somente_com_a_configuracao_reference_date }}
    {% else %}
        {% set the_date = logical_date %}
    {% endif %}
{% endif %}
'''

# to be used in dags
template_reference_date = remove_template_indentation(
    base_template_reference_date +
    '{{ the_date.isoformat() }}'
)

template_last_day_of_month = remove_template_indentation(
    base_template_reference_date + '''
    {% set last_day_of_month = (
        the_date + macros.dateutil.relativedelta.relativedelta(months=+1)
    ).replace(day=1) - macros.timedelta(days=1) %}
'''
)

template_last_day_of_last_month_reference_date = remove_template_indentation(
    base_template_reference_date + '''
    {% set last_day_of_last_month_reference_date =
        the_date.replace(day=1) - macros.timedelta(days=1) %}
    '''
)

template_ano_mes_referencia = (
    template_last_day_of_month.strip() +
    '{{ last_day_of_month.strftime("%Y%m") }}'
)

template_ano_referencia = (
    template_last_day_of_month.strip() +
    '{{ last_day_of_month.strftime("%Y") }}'
)

template_mes_referencia = (
    template_last_day_of_month.strip() +
    '{{ last_day_of_month.strftime("%m") }}'
)

template_ano_mes_dia_referencia = (
    template_last_day_of_month.strip() +
    '{{ last_day_of_month.strftime("%Y%m%d") }}'
)

template_ano_mes_referencia_anterior = (
    template_last_day_of_last_month_reference_date.strip() +
    '{{ last_day_of_last_month_reference_date.strftime("%Y%m") }}'
)

# to be used in templates. Uses the same logic as "get_trigger_date"
# to calculate the DAG's execution start date.
base_template_trigger_date = '''
{% if dag_run.external_trigger is defined and dag_run.external_trigger %}
    {% if dag_run.conf is defined %}
        {% if dag_run.conf["trigger_date"] is defined %}
            {% set the_date = macros.datetime.fromisoformat(dag_run.conf["trigger_date"]) %}
        {% else %}
            {% set the_date = logical_date %}
        {% endif %}
    {% endif %}
{% else %}
    {% set the_date = data_interval_end %}
{% endif %}
'''

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


template_last_day_of_last_month = remove_template_indentation(
    base_template_trigger_date + '''
{% set last_day_of_last_month =
    the_date.replace(day=1) - macros.timedelta(days=1) %}
'''
)

# to be used in dags
template_trigger_date = remove_template_indentation(
    base_template_trigger_date +
    '{{ the_date.isoformat() }}'
)

template_trigger_date_local_time = remove_template_indentation(
    base_template_trigger_date_local_time +
    '{{ the_date.isoformat() }}'
)

template_ano_trigger = remove_template_indentation(
    base_template_trigger_date +
    '{{ the_date.strftime("%Y") }}'
)

template_mes_trigger = remove_template_indentation(
    base_template_trigger_date +
    '{{ the_date.strftime("%m") }}'
)

template_dia_trigger = remove_template_indentation(
    base_template_trigger_date +
    '{{ the_date.strftime("%d") }}'
)

template_ano_mes_trigger = remove_template_indentation(
    base_template_trigger_date +
    '{{ the_date.strftime("%Y%m") }}'
)

template_ano_mes_dia_trigger = remove_template_indentation(
    base_template_trigger_date +
    '{{ the_date.strftime("%Y%m%d") }}'
)

template_ano_mes_dia_trigger_local_time = remove_template_indentation(
    base_template_trigger_date_local_time +
    '{{ the_date.strftime("%d/%m/%Y") }}'
)
