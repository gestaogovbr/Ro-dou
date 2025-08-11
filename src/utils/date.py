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
            "trigger_date", # manual trigger , specifying the variable
            None # or whit a manual trigger , but the variable is not specified
        )
    ) if context["dag_run"] and context["dag_run"].conf else None # It's a predeterminated excution of the dag+

    if context["dag_run"].external_trigger:
        if trigger_date_conf: # triggers manual execution when the configuration is specified
            trigger_date: datetime = datetime.fromisoformat(trigger_date_conf)
        else: # triggers manual execution when the configuration is not specified.
            trigger_date: datetime = context["logical_date"]
            if local_time is True:
                trigger_date = trigger_date.in_timezone(AIRFLOW_TIMEZONE)

    else: # exemple of schedule execution
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