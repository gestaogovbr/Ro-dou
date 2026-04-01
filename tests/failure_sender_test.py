"""Unit tests for FailureSender."""

import json
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from dags.ro_dou_src.notification.failure_sender import FailureSender


@pytest.fixture()
def specs_with_callback():
    specs = MagicMock()
    specs.callback.on_failure_callback = ["dev@email.com", "ops@email.com"]
    return specs


@pytest.fixture()
def specs_without_callback():
    specs = MagicMock()
    specs.callback = None
    return specs


@pytest.fixture()
def specs_callback_empty_list():
    specs = MagicMock()
    specs.callback.on_failure_callback = []
    return specs


@pytest.fixture()
def dag_run():
    dr = MagicMock()
    dr.dag_id = "my_dag"
    dr.run_id = "manual__2024-01-01"
    dr.execution_date = datetime(2024, 1, 1, 12, 0)
    return dr


@pytest.fixture()
def task_instance():
    ti = MagicMock()
    ti.task_id = "my_task"
    ti.state = "failed"
    ti.log_url = "http://airflow/log/1"
    return ti


class TestGetFailureEmailList:
    def test_returns_callback_emails_plus_email_admin(self, specs_with_callback):
        sender = FailureSender(specs_with_callback)
        with patch(
            "dags.ro_dou_src.notification.failure_sender.Variable.get",
            return_value="admin@email.com",
        ):
            result = sender._get_failure_email_list()

        assert "dev@email.com" in result
        assert "ops@email.com" in result
        assert "admin@email.com" in result

    def test_returns_only_email_admin_when_no_callback(self, specs_without_callback):
        sender = FailureSender(specs_without_callback)
        with patch(
            "dags.ro_dou_src.notification.failure_sender.Variable.get",
            return_value="admin@email.com",
        ):
            result = sender._get_failure_email_list()

        assert result == ["admin@email.com"]

    def test_returns_only_callback_when_email_admin_is_none(self, specs_with_callback):
        sender = FailureSender(specs_with_callback)
        with patch(
            "dags.ro_dou_src.notification.failure_sender.Variable.get",
            return_value=None,
        ):
            result = sender._get_failure_email_list()

        assert result == ["dev@email.com", "ops@email.com"]

    def test_returns_empty_list_when_no_callback_and_variable_raises(
        self, specs_without_callback
    ):
        sender = FailureSender(specs_without_callback)
        with patch(
            "dags.ro_dou_src.notification.failure_sender.Variable.get",
            side_effect=Exception("variable not found"),
        ):
            result = sender._get_failure_email_list()

        assert result == []

    def test_returns_empty_list_when_callback_is_empty_and_no_email_admin(
        self, specs_callback_empty_list
    ):
        sender = FailureSender(specs_callback_empty_list)
        with patch(
            "dags.ro_dou_src.notification.failure_sender.Variable.get",
            return_value=None,
        ):
            result = sender._get_failure_email_list()

        assert result == []


class TestSendFailureEmail:
    def test_sends_email_when_list_is_non_empty(
        self, specs_with_callback, dag_run, task_instance
    ):
        sender = FailureSender(specs_with_callback)
        sender.tm = MagicMock()
        sender.tm.renderizar.return_value = "<html>failure</html>"

        with patch(
            "dags.ro_dou_src.notification.failure_sender.send_email"
        ) as mock_send:
            sender.send_failure_email(
                ["dev@email.com"], dag_run, task_instance
            )

        mock_send.assert_called_once()
        call_kwargs = mock_send.call_args
        assert call_kwargs[1]["to"] == ["dev@email.com"]
        assert "my_dag" in call_kwargs[1]["subject"]

    def test_does_not_send_email_when_list_is_empty(
        self, specs_with_callback, dag_run, task_instance
    ):
        sender = FailureSender(specs_with_callback)
        sender.tm = MagicMock()

        with patch(
            "dags.ro_dou_src.notification.failure_sender.send_email"
        ) as mock_send:
            sender.send_failure_email([], dag_run, task_instance)

        mock_send.assert_not_called()

    def test_handles_send_email_exception_gracefully(
        self, specs_with_callback, dag_run, task_instance
    ):
        sender = FailureSender(specs_with_callback)
        sender.tm = MagicMock()
        sender.tm.renderizar.return_value = "<html>failure</html>"

        with patch(
            "dags.ro_dou_src.notification.failure_sender.send_email",
            side_effect=Exception("SMTP error"),
        ):
            # Must not raise
            sender.send_failure_email(["dev@email.com"], dag_run, task_instance)

    def test_formats_execution_date_correctly(
        self, specs_with_callback, dag_run, task_instance
    ):
        sender = FailureSender(specs_with_callback)
        sender.tm = MagicMock()
        sender.tm.renderizar.return_value = "<html>failure</html>"

        with patch("dags.ro_dou_src.notification.failure_sender.send_email"):
            sender.send_failure_email(["dev@email.com"], dag_run, task_instance)

        render_kwargs = sender.tm.renderizar.call_args[1]
        assert render_kwargs["execution_date"] == "01/01/2024 12:00"

    def test_uses_na_when_execution_date_is_none(
        self, specs_with_callback, task_instance
    ):
        sender = FailureSender(specs_with_callback)
        sender.tm = MagicMock()
        sender.tm.renderizar.return_value = "<html>failure</html>"

        dr = MagicMock()
        dr.dag_id = "my_dag"
        dr.run_id = "manual__2024-01-01"
        dr.execution_date = None

        with patch("dags.ro_dou_src.notification.failure_sender.send_email"):
            sender.send_failure_email(["dev@email.com"], dr, task_instance)

        render_kwargs = sender.tm.renderizar.call_args[1]
        assert render_kwargs["execution_date"] == "N/A"


class TestSendSlackFailureNotification:
    def _make_slack_conn(self, channel="#alerts"):
        conn = MagicMock()
        conn.description = json.dumps({"channel": channel})
        return conn

    def test_sends_slack_notification_when_connection_exists(
        self, specs_with_callback, dag_run, task_instance
    ):
        sender = FailureSender(specs_with_callback)
        mock_notifier = MagicMock()

        with patch(
            "dags.ro_dou_src.notification.failure_sender.BaseHook.get_connection",
            return_value=self._make_slack_conn("#alerts"),
        ), patch(
            "dags.ro_dou_src.notification.failure_sender.SlackNotifier",
            return_value=mock_notifier,
        ):
            sender.send_slack_failure_notification(
                {}, dag_run, task_instance, Exception("boom")
            )

        mock_notifier.notify.assert_called_once()

    def test_uses_channel_from_connection_description(
        self, specs_with_callback, dag_run, task_instance
    ):
        sender = FailureSender(specs_with_callback)
        mock_notifier = MagicMock()

        with patch(
            "dags.ro_dou_src.notification.failure_sender.BaseHook.get_connection",
            return_value=self._make_slack_conn("#my-channel"),
        ), patch(
            "dags.ro_dou_src.notification.failure_sender.SlackNotifier",
            return_value=mock_notifier,
        ) as MockSlack:
            sender.send_slack_failure_notification(
                {}, dag_run, task_instance, Exception("boom")
            )

        _, kwargs = MockSlack.call_args
        assert kwargs["channel"] == "#my-channel"

    def test_logs_error_when_connection_not_available(
        self, specs_with_callback, dag_run, task_instance
    ):
        sender = FailureSender(specs_with_callback)

        with patch(
            "dags.ro_dou_src.notification.failure_sender.BaseHook.get_connection",
            side_effect=Exception("connection not found"),
        ):
            # Must not raise
            sender.send_slack_failure_notification(
                {}, dag_run, task_instance, Exception("boom")
            )


class TestSend:
    def test_send_calls_both_email_and_slack(
        self, specs_with_callback, dag_run, task_instance
    ):
        sender = FailureSender(specs_with_callback)
        sender.send_slack_failure_notification = MagicMock()
        sender.send_failure_email = MagicMock()
        sender._get_failure_email_list = MagicMock(return_value=["dev@email.com"])

        sender.send({}, dag_run, task_instance, Exception("boom"))

        sender.send_slack_failure_notification.assert_called_once()
        sender.send_failure_email.assert_called_once()
