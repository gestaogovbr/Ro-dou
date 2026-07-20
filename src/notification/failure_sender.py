"""Module for sending notifications."""

import os
import sys
import logging

import json

# Add parent folder to sys.path in order to be able to import
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from airflow.utils.email import send_email

from airflow.hooks.base import BaseHook
from airflow.models import Variable

from airflow.providers.slack.notifications.slack import SlackNotifier

from parsers import DAGConfig
from typing import List

from notification.templateManager import TemplateManager


class FailureSender:
    """Sends DAG failure notifications via email.

    Resolves recipients from `DAGConfig.callback.on_failure_callback`. The
    `email_admin` Airflow variable is always appended when available; if it is
    not set, `DAGConfig.report.emails` is used as a fallback. The notification
    is rendered from an HTML template and sent via Airflow's `send_email`.

    Attributes:
        specs (DAGConfig): DAG configuration, including failure callbacks.
        tm (TemplateManager): HTML template manager for email rendering.
    """

    SLACK_CONN_ID = "slack_notify_rodou_dagrun"

    def __init__(self, specs: DAGConfig) -> None:
        self.specs = specs
        self.tm = TemplateManager(
            template_dir=os.path.join(os.path.dirname(__file__), "templates")
        )

    def send(self, context, dag_run, task_instance, exception):
        """Sends failure notification via email and Slack."""
        if self.SLACK_CONN_ID:
            self.send_slack_failure_notification(
                context, dag_run, task_instance, exception
            )
        self.send_failure_email(self._get_failure_email_list(), dag_run, task_instance)

    def _get_failure_email_list(self) -> List[str]:
        """Resolves the list of recipient emails for failure notifications."""
        # Determina lista de emails para notificação
        email_list = []

        if self.specs.callback and self.specs.callback.on_failure_callback:
            logging.error(
                "Using failure callback emails from DAG configuration: %s",
                self.specs.callback.on_failure_callback,
            )
            # Usa emails configurados no .yaml
            email_list = self.specs.callback.on_failure_callback

        if not email_list:
            logging.warning(
                "No email configured for failure notification (neither callback nor email_admin variable)"
            )

        # Usa email admin padrão
        try:
            email_admin = Variable.get("email_admin", default_var=None)
            if email_admin:
                return email_list + [email_admin]
            # Se email_admin não estiver configurado, verifica se há email no relatório do DAG
            else:
                return (
                    email_list + self.specs.report.emails
                    if self.specs.report and self.specs.report.emails
                    else email_list
                )
        except Exception as e:
            logging.error(f"Error getting email_admin variable: {str(e)}")

        return email_list

    def send_failure_email(self, email_list: List[str], dag_run, task_instance):
        """Sends failure notification email to the provided recipients."""

        execution_date_str = (
            dag_run.execution_date.strftime("%d/%m/%Y %H:%M")
            if dag_run.execution_date
            else "N/A"
        )
        if email_list:
            try:

                html_content = self.tm.renderizar(
                    "failure_template.html",
                    task_id=task_instance.task_id,
                    execution_date=execution_date_str,
                    dag_run_id=dag_run.run_id,
                    log_url=task_instance.log_url,
                )

                send_email(
                    to=email_list,
                    subject=f"Falha na DAG {dag_run.dag_id}",
                    html_content=html_content,
                )
                logging.info(f"Failure notification email sent to: {email_list}")
            except Exception as e:
                logging.error(
                    f"Failed to send failure notification email: {str(e)}",
                    exc_info=True,
                )

    def send_slack_failure_notification(
        self, context, dag_run, task_instance, exception
    ):
        """Sends failure notification via Slack, if the connection is available."""
        try:
            conn = BaseHook.get_connection(self.SLACK_CONN_ID)
            description = json.loads(conn.description)
            slack_notifier = SlackNotifier(
                slack_conn_id=self.SLACK_CONN_ID,
                text=(
                    ":bomb: *Falha na DAG*"
                    f"\n📊 *DAG:* `{dag_run.dag_id}`"
                    f"\n📋 *Task:* `{task_instance.task_id}`"
                    f"\n*State:* `{task_instance.state}`"
                    f"\n 📅 *Data de execução:* {dag_run.execution_date.strftime('%d/%m/%Y %H:%M') if dag_run.execution_date else 'N/A'}"
                    f"\n📁 *Exception:* {exception}"
                    f"\n🔗 *Log:* <{task_instance.log_url}|Ver log completo>"
                ),
                channel=description["channel"],
            )
            slack_notifier.notify(context)
        except Exception as e:
            logging.error(f"Slack notification not sent: {str(e)}")
