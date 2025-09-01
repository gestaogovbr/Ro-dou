from collections import namedtuple
from unittest.mock import Mock, MagicMock, patch
import pytest
from pytest_mock import MockerFixture

from dags.ro_dou_src.notification.notifier import Notifier
from dags.ro_dou_src.notification.slack_sender import (    
    _format_date,
    _remove_html_tags,
)

@pytest.fixture
def mock_dag_config_all_notifications():
    """Mock DAGConfig with all notification types enabled"""
    MockDAGConfig = namedtuple("MockDAGConfig", ["report"])
    MockReportConfig = namedtuple(
        "MockReportConfig", 
        [
            "emails", 
            "discord", 
            "slack",
            "notification"
        ]
    )
    
    report = MockReportConfig(
        emails=["test@example.com"],
        discord={
            "webhook_url": "https://discord.com/webhook"
            },
        slack={
            "webhook_url": "https://slack.com/webhook"
        },
        notification={
            "serviceId": "discord", 
            "webhookId": "123", 
            "webhookToken": "abc"
        }
    )
    
    return MockDAGConfig(report=report)


@pytest.fixture
def mock_dag_config_email_only():
    """Mock DAGConfig with only email notifications"""
    MockDAGConfig = namedtuple("MockDAGConfig", ["report"])
    MockReportConfig = namedtuple(
        "MockReportConfig", 
        [
            "emails",
            "discord", 
            "slack", 
            "notification"
        ]
    )
    
    report = MockReportConfig(
        emails=["test@example.com"],
        discord=None,
        slack=None,
        notification=None
    )
    
    return MockDAGConfig(report=report)


@pytest.fixture
def mock_dag_config_no_notifications():
    """Mock DAGConfig with no notifications enabled"""
    MockDAGConfig = namedtuple("MockDAGConfig", ["report"])
    MockReportConfig = namedtuple(
        "MockReportConfig", 
        [
            "emails", 
            "discord", 
            "slack", 
            "notification"
        ]
    )
    
    report = MockReportConfig(
        emails=None,
        discord=None,
        slack=None,
        notification=None
    )
    
    return MockDAGConfig(report=report)

class TestNotifierInit:
    """Test Notifier initialization with different configurations"""
    
    @patch('dags.ro_dou_src.notification.notifier.EmailSender')
    @patch('dags.ro_dou_src.notification.notifier.DiscordSender')
    @patch('dags.ro_dou_src.notification.notifier.SlackSender')
    @patch('dags.ro_dou_src.notification.notifier.NotificationSender')
    def test_init_all_senders(self, mock_notification, mock_slack, mock_discord, mock_email, mock_dag_config_all_notifications):
        """Test that all sender types are initialized when configured"""
        notifier = Notifier(mock_dag_config_all_notifications)
        
        assert len(notifier.senders) == 4
        mock_email.assert_called_once_with(mock_dag_config_all_notifications.report)
        mock_discord.assert_called_once_with(mock_dag_config_all_notifications.report)
        mock_slack.assert_called_once_with(mock_dag_config_all_notifications.report)
        mock_notification.assert_called_once_with(mock_dag_config_all_notifications.report)

    @patch('dags.ro_dou_src.notification.notifier.EmailSender')
    @patch('dags.ro_dou_src.notification.notifier.DiscordSender')
    @patch('dags.ro_dou_src.notification.notifier.SlackSender')
    @patch('dags.ro_dou_src.notification.notifier.NotificationSender')
    def test_init_email_only(self, mock_notification, mock_slack, mock_discord, mock_email, mock_dag_config_email_only):
        """Test that only EmailSender is initialized when only email is configured"""
        notifier = Notifier(mock_dag_config_email_only)
        
        assert len(notifier.senders) == 1
        mock_email.assert_called_once_with(mock_dag_config_email_only.report)
        mock_discord.assert_not_called()
        mock_slack.assert_not_called()
        mock_notification.assert_not_called()

    @patch('dags.ro_dou_src.notification.notifier.EmailSender')
    @patch('dags.ro_dou_src.notification.notifier.DiscordSender')
    @patch('dags.ro_dou_src.notification.notifier.SlackSender')
    @patch('dags.ro_dou_src.notification.notifier.NotificationSender')
    def test_init_no_senders(self, mock_notification, mock_slack, mock_discord, mock_email, mock_dag_config_no_notifications):
        """Test that no senders are initialized when no notifications are configured"""
        notifier = Notifier(mock_dag_config_no_notifications)
        
        assert len(notifier.senders) == 0
        mock_email.assert_not_called()
        mock_discord.assert_not_called()
        mock_slack.assert_not_called()
        mock_notification.assert_not_called()

class TestUtilityFunctions:
    def test_format_date_monday(self):
        result = _format_date("13/03/2023")  # This is a Monday
        assert result == "Seg 13/03"

    def test_format_date_friday(self):
        result = _format_date("17/03/2023")  # This is a Friday
        assert result == "Sex 17/03"

    def test_format_date_sunday(self):
        result = _format_date("19/03/2023")  # This is a Sunday
        assert result == "Dom 19/03"

    def test_remove_html_tags_simple(self):
        html_text = "<p>This is a <strong>test</strong></p>"
        result = _remove_html_tags(html_text)
        assert result == "This is a test"

    def test_remove_html_tags_complex(self):
        html_text = '<div class="content"><h1>Title</h1><p>Paragraph with <a href="link">link</a></p></div>'
        result = _remove_html_tags(html_text)
        assert result == "TitleParagraph with link"

    def test_remove_html_tags_no_html(self):
        plain_text = "This is plain text"
        result = _remove_html_tags(plain_text)
        assert result == "This is plain text"

    def test_remove_html_tags_empty_string(self):
        result = _remove_html_tags("")
        assert result == ""
        
class TestNotifierSendNotification:
    """Test Notifier send_notification method"""
    
    def test_send_notification_calls_all_senders(self, mock_dag_config_email_only):
        """Test that send_notification calls send_report on all configured senders"""
        notifier = Notifier(mock_dag_config_email_only)
        
        # Mock the sender
        mock_sender = Mock()
        notifier.senders = [mock_sender]
        
        search_report = "Test report content"
        report_date = "2025-09-01"
        
        notifier.send_notification(search_report, report_date)
        
        mock_sender.send_report.assert_called_once_with(search_report, report_date)

    def test_send_notification_no_senders(self, mock_dag_config_no_notifications):
        """Test that send_notification handles case with no senders gracefully"""
        notifier = Notifier(mock_dag_config_no_notifications)
        
        search_report = "Test report content"
        report_date = "2025-09-01"
        
        # Não deve levantar nenhuma exceção
        notifier.send_notification(search_report, report_date)

    def test_send_notification_sender_exception(self, mock_dag_config_email_only):
        """Test that send_notification continues if one sender raises an exception"""
        notifier = Notifier(mock_dag_config_email_only)
        
        # Remetentes simulados onde um deles gera uma exceção
        mock_sender1 = Mock()
        mock_sender1.send_report.side_effect = Exception("Network error")
        mock_sender2 = Mock()
        
        notifier.senders = [mock_sender1, mock_sender2]
        
        search_report = "Test report content"
        report_date = "2025-09-01"
        
        # Deve continuar a enviar o segundo remetente mesmo que o primeiro falhe
        with pytest.raises(Exception, match="Network error"):
            notifier.send_notification(search_report, report_date)
        
        mock_sender1.send_report.assert_called_once_with(search_report, report_date)

class TestNotifierIntegration:
    """Integration tests for Notifier class"""
    
    @patch('dags.ro_dou_src.notification.notifier.EmailSender')
    def test_notifier_with_real_email_config(self, mock_email_sender, mock_dag_config_email_only):
        """Test Notifier with realistic email configuration"""
        mock_email_instance = Mock()
        mock_email_sender.return_value = mock_email_instance
        
        notifier = Notifier(mock_dag_config_email_only)

        # Verifica se o EmailSender foi criado
        assert len(notifier.senders) == 1
        mock_email_sender.assert_called_once_with(mock_dag_config_email_only.report)
        
        # Test notification sending
        notifier.send_notification("Test report", "2025-09-01")
        mock_email_instance.send_report.assert_called_once_with("Test report", "2025-09-01")

    def test_notifier_type_annotations(self, mock_dag_config_no_notifications):
        """Test that senders attribute has correct type"""
        notifier = Notifier(mock_dag_config_no_notifications)

        # Verifica se o senders é uma lista
        assert isinstance(notifier.senders, list)
        assert len(notifier.senders) == 0