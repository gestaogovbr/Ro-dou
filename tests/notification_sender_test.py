from collections import namedtuple
from unittest.mock import Mock, MagicMock, patch

import pytest
import apprise
from pytest_mock import MockerFixture

from dags.ro_dou_src.notification.notification_sender import NotificationSender


@pytest.fixture
def mock_report_config():
    """Mock ReportConfig for testing"""
    MockReportConfig = namedtuple(
        "MockReportConfig",
        [
            "notification",
            "hide_filters", 
            "header_text",
            "footer_text",
            "no_results_found_text"
        ]
    )
    return MockReportConfig(
        notification={
            'serviceId': 'discord',
            'webhookId': 'test_webhook_id',
            'webhookToken': 'test_webhook_token'
        },
        hide_filters=False,
        header_text="Test Header",
        footer_text="Test Footer", 
        no_results_found_text="Nenhum resultado encontrado"
    )


@pytest.fixture
def mock_report_config_no_filters():
    """Mock ReportConfig with hide_filters=True"""
    MockReportConfig = namedtuple(
        "MockReportConfig",
        [
            "notification",
            "hide_filters",
            "header_text", 
            "footer_text",
            "no_results_found_text"
        ]
    )
    return MockReportConfig(
        notification={
            'serviceId': 'slack://',
            'webhookId': 'test_webhook_id',
            'webhookToken': 'test_webhook_token'
        },
        hide_filters=True,
        header_text="<h1>HTML Header</h1>",
        footer_text="<p>HTML Footer</p>",
        no_results_found_text="No results"
    )


class TestNotificationSenderInit:
    def test_init_with_valid_config(self, mock_report_config):
        sender = NotificationSender(mock_report_config)
        
        assert sender.notification == mock_report_config.notification
        assert sender.hide_filters == mock_report_config.hide_filters
        assert sender.header_text == mock_report_config.header_text
        assert sender.footer_text == mock_report_config.footer_text
        assert sender.no_results_found_text == mock_report_config.no_results_found_text
        assert isinstance(sender.apobj, apprise.Apprise)


class TestNotificationSenderTextProcessing:
    def test_remove_html_tags(self, mock_report_config):
        sender = NotificationSender(mock_report_config)
        
        assert sender._remove_html_tags("<h1>Title</h1>") == "Title"
        assert sender._remove_html_tags("<p>Text with <b>bold</b></p>") == "Text with bold"
        assert sender._remove_html_tags("Plain text") == "Plain text"
        assert sender._remove_html_tags("") == ""
        assert sender._remove_html_tags(None) is None
        assert sender._remove_html_tags(123) == 123

    def test_remove_tag_from_serviceId(self, mock_report_config):
        sender = NotificationSender(mock_report_config)
        
        assert sender._remove_tag_from_serviceId("discord://") == "discord"
        assert sender._remove_tag_from_serviceId("slack://") == "slack"
        assert sender._remove_tag_from_serviceId("discord") == "discord"
        assert sender._remove_tag_from_serviceId("") == ""


class TestNotificationSenderDataConversion:
    def test_convert_dou_data_to_apprise_with_embeds(self, mock_report_config):
        sender = NotificationSender(mock_report_config)
        
        data = {
            "embeds": [
                {
                    "title": "Test Title",
                    "description": "Test Description", 
                    "url": "https://example.com"
                },
                {
                    "title": "Another Title",
                    "description": "Another Description",
                    "url": "https://another.com"
                }
            ]
        }
        
        result = sender._convert_dou_data_to_apprise(data)
       
        expected = """*Test Title*
                Test Description
                   https://example.com

                  *Another Title*

                Another Description
                  https://another.com

                """
        assert len(result.split('\n')) == len(expected.split('\n'))

    def test_convert_dou_data_to_apprise_with_content(self, mock_report_config):
        sender = NotificationSender(mock_report_config)
        
        data = {"content": "Simple text content"}
        result = sender._convert_dou_data_to_apprise(data)
        
        assert result == "Simple text content\n"

    def test_convert_dou_data_to_apprise_with_partial_embed(self, mock_report_config):
        sender = NotificationSender(mock_report_config)
        
        data = {
            "embeds": [
                {
                    "title": "Only Title"
                }
            ]
        }
        
        result = sender._convert_dou_data_to_apprise(data)
        expected = "📋 *Only Title*\n"
        assert result == expected

    def test_convert_dou_data_to_apprise_empty_data(self, mock_report_config):
        sender = NotificationSender(mock_report_config)
        
        result = sender._convert_dou_data_to_apprise({})
        assert result == ""


class TestNotificationSenderSendMethods:
    def test_send_text(self, session_mocker: MockerFixture, mock_report_config):
        sender = NotificationSender(mock_report_config)
        mock_send_data = session_mocker.patch.object(sender, 'send_data')
        
        sender.send_text("Test content")
        
        mock_send_data.assert_called_once_with({"content": "Test content"})

    def test_send_embeds(self, session_mocker: MockerFixture, mock_report_config):
        sender = NotificationSender(mock_report_config)
        mock_send_data = session_mocker.patch.object(sender, 'send_data')
        
        items = [
            {
                "title": "Title 1",
                "abstract": "Abstract 1", 
                "href": "https://example1.com"
            },
            {
                "title": "Title 2",
                "abstract": "Abstract 2",
                "href": "https://example2.com"
            }
        ]
        
        sender.send_embeds(items)
        
        expected_data = {
            "embeds": [
                {
                    "title": "Title 1",
                    "description": "Abstract 1",
                    "url": "https://example1.com"
                },
                {
                    "title": "Title 2", 
                    "description": "Abstract 2",
                    "url": "https://example2.com"
                }
            ]
        }
        mock_send_data.assert_called_once_with(expected_data)

    @patch('dags.ro_dou_src.notification.notification_sender.apprise.Apprise')
    def test_send_data(self, mock_apprise_class, mock_report_config):
        mock_apprise_instance = MagicMock()
        mock_apprise_class.return_value = mock_apprise_instance
        
        sender = NotificationSender(mock_report_config)
        
        data = {"content": "Test message"}
        sender.send_data(data)
        
        expected_url = "discord://test_webhook_id/test_webhook_token"
        mock_apprise_instance.add.assert_called_once_with(expected_url)
        mock_apprise_instance.notify.assert_called_once_with(
            body="Test message\n",
            title="Test Header"
        )

    @patch('dags.ro_dou_src.notification.notification_sender.apprise.Apprise')
    def test_send_data_with_html_header(self, mock_apprise_class, mock_report_config_no_filters):
        mock_apprise_instance = MagicMock()
        mock_apprise_class.return_value = mock_apprise_instance
        
        sender = NotificationSender(mock_report_config_no_filters)
        
        data = {"content": "Test message"}
        sender.send_data(data)
        
        mock_apprise_instance.notify.assert_called_once_with(
            body="Test message\n",
            title="HTML Header"
        )

    @patch('dags.ro_dou_src.notification.notification_sender.apprise.Apprise')
    def test_send_data_no_header(self, mock_apprise_class, mock_report_config):
        mock_apprise_instance = MagicMock()
        mock_apprise_class.return_value = mock_apprise_instance
        
        # Create config without header
        config = mock_report_config._replace(header_text=None)
        sender = NotificationSender(config)
        
        data = {"content": "Test message"}
        sender.send_data(data)
        
        mock_apprise_instance.notify.assert_called_once_with(
            body="Test message\n",
            title="Nova Notificação"
        )


class TestNotificationSenderProcessMethods:
    def test_process_search_section(self, session_mocker: MockerFixture, mock_report_config):
        sender = NotificationSender(mock_report_config)
        mock_send_text = session_mocker.patch.object(sender, 'send_text')
        mock_process_group = session_mocker.patch.object(sender, '_process_group')
        
        search = {
            "header": "Test Search Header",
            "result": {
                "group1": {"term1": {"dept1": []}},
                "group2": {"term2": {"dept2": []}}
            }
        }
        
        sender._process_search_section(search)
        
        mock_send_text.assert_called_once_with("**Test Search Header**")
        assert mock_process_group.call_count == 2
        mock_process_group.assert_any_call("group1", {"term1": {"dept1": []}})
        mock_process_group.assert_any_call("group2", {"term2": {"dept2": []}})

    def test_process_search_section_no_header(self, session_mocker: MockerFixture, mock_report_config):
        sender = NotificationSender(mock_report_config)
        mock_send_text = session_mocker.patch.object(sender, 'send_text')
        mock_process_group = session_mocker.patch.object(sender, '_process_group')
        
        search = {
            "result": {
                "group1": {"term1": {"dept1": []}}
            }
        }
        
        sender._process_search_section(search)
        
        mock_send_text.assert_not_called()
        mock_process_group.assert_called_once_with("group1", {"term1": {"dept1": []}})

    def test_process_group_with_filters(self, session_mocker: MockerFixture, mock_report_config):
        sender = NotificationSender(mock_report_config)
        mock_send_text = session_mocker.patch.object(sender, 'send_text')
        mock_process_term = session_mocker.patch.object(sender, '_process_term_results')
        
        search_results = {
            "term1": {"dept1": []},
            "term2": {"dept2": []}
        }
        
        sender._process_group("test_group", search_results)
        
        mock_send_text.assert_called_once_with("**Grupo: test_group**")
        assert mock_process_term.call_count == 2

    def test_process_group_hidden_filters(self, session_mocker: MockerFixture, mock_report_config_no_filters):
        sender = NotificationSender(mock_report_config_no_filters)
        mock_send_text = session_mocker.patch.object(sender, 'send_text')
        mock_process_term = session_mocker.patch.object(sender, '_process_term_results')
        
        search_results = {"term1": {"dept1": []}}
        
        sender._process_group("test_group", search_results)
        
        mock_send_text.assert_not_called()
        mock_process_term.assert_called_once()

    def test_process_group_single_group(self, session_mocker: MockerFixture, mock_report_config):
        sender = NotificationSender(mock_report_config)
        mock_send_text = session_mocker.patch.object(sender, 'send_text')
        mock_process_term = session_mocker.patch.object(sender, '_process_term_results')
        
        search_results = {"term1": {"dept1": []}}
        
        sender._process_group("single_group", search_results)
        
        mock_send_text.assert_not_called()
        mock_process_term.assert_called_once()

    def test_process_term_results_no_results(self, session_mocker: MockerFixture, mock_report_config):
        sender = NotificationSender(mock_report_config)
        mock_send_text = session_mocker.patch.object(sender, 'send_text')
        mock_process_dept = session_mocker.patch.object(sender, '_process_department_results')
        
        sender._process_term_results("test_term", {})
        
        mock_send_text.assert_called_once_with("**Nenhum resultado encontrado**")
        mock_process_dept.assert_not_called()

    def test_process_term_results_with_results(self, session_mocker: MockerFixture, mock_report_config):
        sender = NotificationSender(mock_report_config)
        mock_send_text = session_mocker.patch.object(sender, 'send_text')
        mock_process_dept = session_mocker.patch.object(sender, '_process_department_results')
        
        term_results = {"dept1": [], "dept2": []}
        
        sender._process_term_results("custom_term", term_results)
        
        mock_send_text.assert_called_once_with("**Resultados para: custom_term**")
        assert mock_process_dept.call_count == 2

    def test_process_term_results_all_publications(self, session_mocker: MockerFixture, mock_report_config):
        sender = NotificationSender(mock_report_config)
        mock_send_text = session_mocker.patch.object(sender, 'send_text')
        mock_process_dept = session_mocker.patch.object(sender, '_process_department_results')
        
        term_results = {"dept1": []}
        
        sender._process_term_results("all_publications", term_results)
        
        # Should not send term header for "all_publications"
        mock_send_text.assert_not_called()
        mock_process_dept.assert_called_once()

    def test_process_department_results(self, session_mocker: MockerFixture, mock_report_config):
        sender = NotificationSender(mock_report_config)
        mock_send_text = session_mocker.patch.object(sender, 'send_text')
        mock_send_embeds = session_mocker.patch.object(sender, 'send_embeds')
        
        results = [{"title": "Test", "abstract": "Test abstract", "href": "http://test.com"}]
        
        sender._process_department_results("Test Department", results)
        
        mock_send_text.assert_called_once_with("Test Department")
        mock_send_embeds.assert_called_once_with(results)

    def test_process_department_results_single_department(self, session_mocker: MockerFixture, mock_report_config):
        sender = NotificationSender(mock_report_config)
        mock_send_text = session_mocker.patch.object(sender, 'send_text')
        mock_send_embeds = session_mocker.patch.object(sender, 'send_embeds')
        
        results = []
        
        sender._process_department_results("single_department", results)
        
        mock_send_text.assert_not_called()
        mock_send_embeds.assert_called_once_with(results)


class TestNotificationSenderSend:
    def test_send_complete_report(self, session_mocker: MockerFixture, mock_report_config):
        sender = NotificationSender(mock_report_config)
        mock_send_text = session_mocker.patch.object(sender, 'send_text')
        mock_process_search = session_mocker.patch.object(sender, '_process_search_section')
        
        search_report = [
            {"header": "Search 1", "result": {}},
            {"header": "Search 2", "result": {}}
        ]
        
        sender.send(search_report)
        
        # Should send header, process searches, then send footer
        assert mock_send_text.call_count == 2
        mock_send_text.assert_any_call("Test Header")
        mock_send_text.assert_any_call("Test Footer")
        
        assert mock_process_search.call_count == 2

    def test_send_no_header_footer(self, session_mocker: MockerFixture, mock_report_config):
        # Create config without header/footer
        config = mock_report_config._replace(header_text=None, footer_text=None)
        sender = NotificationSender(config)
        mock_send_text = session_mocker.patch.object(sender, 'send_text')
        mock_process_search = session_mocker.patch.object(sender, '_process_search_section')
        
        search_report = [{"header": "Search 1", "result": {}}]
        
        sender.send(search_report)
        
        mock_send_text.assert_not_called()
        mock_process_search.assert_called_once()

    def test_send_with_date_parameter(self, session_mocker: MockerFixture, mock_report_config):
        sender = NotificationSender(mock_report_config)
        mock_process_search = session_mocker.patch.object(sender, '_process_search_section')
        
        search_report = [{"header": "Search 1", "result": {}}]
        
        # Date parameter is accepted but currently unused
        sender.send(search_report, report_date="2023-01-01")
        
        mock_process_search.assert_called_once()