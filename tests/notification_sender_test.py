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
            "serviceId": "discord://",
            "webhookId": "123456789",
            "webhookToken": "abcdef123"
        },
        hide_filters=False,
        header_text="Test Header",
        footer_text="Test Footer", 
        no_results_found_text="Nenhum resultado encontrado"
    )


@pytest.fixture
def mock_report_config_no_header_footer():
    """Mock ReportConfig without header and footer for testing"""
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
            "serviceId": "discord",
            "webhookId": "123456789",
            "webhookToken": "abcdef123"
        },
        hide_filters=True,
        header_text=None,
        footer_text=None, 
        no_results_found_text="No results"
    )


@pytest.fixture
def sample_search_report():
    """Sample search report for testing"""
    return [
        {
            "header": "Seção 3",
            "department": ["Departamento A"],
            "department_ignore": ["Departamento B"],
            "pubtype": ["Tipo 1", "Tipo 2"],
            "result": {
                "group_1": {
                    "term_1": {
                        "Department A": [
                            {
                                "section": "Seção 3",
                                "title": "EXTRATO DE COMPROMISSO",
                                "href": "https://www.in.gov.br/web/dou/-/extrato-de-compromisso-342504508",
                                "abstract": "ALESSANDRO GLAUCO DOS ANJOS DE VASCONCELOS - Secretário-Executivo Adjunto...",
                                "date": "02/09/2021",
                                "arttype": [
                                    "Edital",
                                    "Ata", 
                                    "Portaria",
                                ],
                            },
                        ],
                    },
                },
            },
        },
    ]


@pytest.fixture
def empty_search_report():
    """Empty search report for testing no results scenario"""
    return [
        {
            "department": [],
            "department_ignore": [],
            "pubtype": [],
            "result": {},
        }
    ]


class TestNotificationSenderInit:
    """Test NotificationSender initialization"""
    
    def test_init_with_valid_config(self, mock_report_config):
        sender = NotificationSender(mock_report_config)
        
        assert sender.notification == mock_report_config.notification
        assert sender.hide_filters == mock_report_config.hide_filters
        assert sender.header_text == mock_report_config.header_text
        assert sender.footer_text == mock_report_config.footer_text
        assert sender.no_results_found_text == mock_report_config.no_results_found_text
        assert isinstance(sender.apobj, apprise.Apprise)
        assert sender.message == ""

    def test_init_with_no_header_footer(self, mock_report_config_no_header_footer):
        sender = NotificationSender(mock_report_config_no_header_footer)
        
        assert sender.header_text is None
        assert sender.footer_text is None
        assert sender.hide_filters is True


class TestNotificationSenderSend:
    """Test NotificationSender send method"""
    
    @patch('dags.ro_dou_src.notification.notification_sender.apprise.Apprise')
    def test_send_with_header(self, mock_apprise_class, mock_report_config, sample_search_report):
        mock_apprise_instance = MagicMock()
        mock_apprise_class.return_value = mock_apprise_instance
        
        sender = NotificationSender(mock_report_config)
        sender.send(sample_search_report, "2024-04-01")
        
        assert "Test Header" in sender.message
        assert "**Seção 3**" in sender.message

    @patch('dags.ro_dou_src.notification.notification_sender.apprise.Apprise')
    def test_send_without_header(self, mock_apprise_class, mock_report_config_no_header_footer, sample_search_report):
        mock_apprise_instance = MagicMock()
        mock_apprise_class.return_value = mock_apprise_instance
        
        sender = NotificationSender(mock_report_config_no_header_footer)
        sender.send(sample_search_report, "2024-04-01")
        
        assert "Test Header" not in sender.message
        assert "**Seção 3**" in sender.message

    @patch('dags.ro_dou_src.notification.notification_sender.apprise.Apprise')
    def test_send_with_empty_report(self, mock_apprise_class, mock_report_config, empty_search_report):
        mock_apprise_instance = MagicMock()
        mock_apprise_class.return_value = mock_apprise_instance

        sender = NotificationSender(mock_report_config)
        sender.send(empty_search_report, "2024-04-01")

        assert mock_apprise_instance.notify.call_count == 0        

class TestNotificationSenderProcessSearchSection:
    """Test NotificationSender _process_search_section method"""
    
    def test_process_search_section_with_header(self, mock_report_config):
        sender = NotificationSender(mock_report_config)
        search = {
            "header": "Seção 3",
            "result": {
                "group_1": {
                    "term_1": {
                        "Department A": []
                    }
                }
            }
        }
        
        sender._process_search_section(search)
        
        assert "**Seção 3**" in sender.message

    def test_process_search_section_without_header(self, mock_report_config):
        sender = NotificationSender(mock_report_config)
        search = {
            "result": {
                "group_1": {
                    "term_1": {
                        "Department A": []
                    }
                }
            }
        }
        
        initial_message = sender.message
        sender._process_search_section(search)
        
        # Message should not contain any section header
        assert "**Seção" not in sender.message

    def test_process_search_section_empty_result(self, mock_report_config):
        sender = NotificationSender(mock_report_config)
        search = {
            "header": "Seção 1",
            "result": {}
        }
        
        sender._process_search_section(search)
        
        assert "**Seção 1**" in sender.message


class TestNotificationSenderProcessGroup:
    """Test NotificationSender _process_group method"""
    
    def test_process_group_with_filters_visible(self, mock_report_config):
        sender = NotificationSender(mock_report_config)
        group_name = "custom_group"
        search_results = {
            "term_1": {
                "Department A": []
            }
        }
        
        with patch.object(sender, 'send_text') as mock_send_text:
            sender._process_group(group_name, search_results)
            mock_send_text.assert_called_once_with("**Grupo: custom_group**")

    def test_process_group_with_filters_hidden(self, mock_report_config_no_header_footer):
        sender = NotificationSender(mock_report_config_no_header_footer)
        group_name = "custom_group"
        search_results = {
            "term_1": {
                "Department A": []
            }
        }
        
        with patch.object(sender, 'send_text') as mock_send_text:
            sender._process_group(group_name, search_results)
            mock_send_text.assert_not_called()

    def test_process_group_single_group_no_header(self, mock_report_config):
        sender = NotificationSender(mock_report_config)
        group_name = "single_group"
        search_results = {
            "term_1": {
                "Department A": []
            }
        }
        
        with patch.object(sender, 'send_text') as mock_send_text:
            sender._process_group(group_name, search_results)
            mock_send_text.assert_not_called()


class TestNotificationSenderProcessTermResults:
    """Test NotificationSender _process_term_results method"""
    
    def test_process_term_results_with_results(self, mock_report_config):
        sender = NotificationSender(mock_report_config)
        term = "custom_term"
        term_results = {
            "Department A": [
                {
                    "section": "Seção 3",
                    "title": "Test Title",
                    "href": "https://example.com",
                    "abstract": "Test abstract",
                    "date": "01/01/2024"
                }
            ]
        }
        
        sender._process_term_results(term, term_results)
        
        assert "**Resultados para: custom_term**" in sender.message

    def test_process_term_results_all_publications_no_header(self, mock_report_config):
        sender = NotificationSender(mock_report_config)
        term = "all_publications"
        term_results = {
            "Department A": [
                {
                    "section": "Seção 3",
                    "title": "Test Title",
                    "href": "https://example.com",
                    "abstract": "Test abstract",
                    "date": "01/01/2024"
                }
            ]
        }
        
        sender._process_term_results(term, term_results)
        
        assert "**Resultados para: all_publications**" not in sender.message

    def test_process_term_results_empty_with_filters_visible(self, mock_report_config):
        sender = NotificationSender(mock_report_config)
        term = "empty_term"
        term_results = {}
        
        with patch.object(sender, 'send_text') as mock_send_text:
            sender._process_term_results(term, term_results)
            mock_send_text.assert_called_once()

    def test_process_term_results_empty_with_filters_hidden(self, mock_report_config_no_header_footer):
        sender = NotificationSender(mock_report_config_no_header_footer)
        term = "empty_term"
        term_results = {}
        
        with patch.object(sender, 'send_text') as mock_send_text:
            sender._process_term_results(term, term_results)
            mock_send_text.assert_not_called()


class TestNotificationSenderProcessDepartmentResults:
    """Test NotificationSender _process_department_results method"""
    
    def test_process_department_results_with_filters_visible(self, mock_report_config):
        sender = NotificationSender(mock_report_config)
        department = "Custom Department"
        results = [
            {
                "section": "Seção 3",
                "title": "Test Title",
                "href": "https://example.com",
                "abstract": "Test abstract",
                "date": "01/01/2024"
            }
        ]
        
        sender._process_department_results(department, results)
        
        assert "**Unidade: Custom Department**" in sender.message

    def test_process_department_results_single_department_no_header(self, mock_report_config):
        sender = NotificationSender(mock_report_config)
        department = "single_department"
        results = [
            {
                "section": "Seção 3",
                "title": "Test Title",
                "href": "https://example.com",
                "abstract": "Test abstract",
                "date": "01/01/2024"
            }
        ]
        
        sender._process_department_results(department, results)
        
        assert "**Departamento: single_department**" not in sender.message

    def test_process_department_results_with_filters_hidden(self, mock_report_config_no_header_footer):
        sender = NotificationSender(mock_report_config_no_header_footer)
        department = "Custom Department"
        results = [
            {
                "section": "Seção 3",
                "title": "Test Title",
                "href": "https://example.com",
                "abstract": "Test abstract",
                "date": "01/01/2024"
            }
        ]
        
        sender._process_department_results(department, results)
        
        assert "**Departamento: Custom Department**" not in sender.message


class TestNotificationSenderSendText:
    """Test NotificationSender send_text method"""
    
    @patch('dags.ro_dou_src.notification.notification_sender.apprise.Apprise')
    def test_send_text_with_footer(self, mock_apprise_class, mock_report_config):
        mock_apprise_instance = MagicMock()
        mock_apprise_class.return_value = mock_apprise_instance
        
        sender = NotificationSender(mock_report_config)
        content = "Test content"
        
        with patch.object(sender, 'send_data') as mock_send_data:
            sender.send_text(content)
            
            expected_content = content + "Test Footer" + "\n"
            mock_send_data.assert_called_once_with({"content": expected_content})

    @patch('dags.ro_dou_src.notification.notification_sender.apprise.Apprise')
    def test_send_text_without_footer(self, mock_apprise_class, mock_report_config_no_header_footer):
        mock_apprise_instance = MagicMock()
        mock_apprise_class.return_value = mock_apprise_instance
        
        sender = NotificationSender(mock_report_config_no_header_footer)
        content = "Test content"
        
        with patch.object(sender, 'send_data') as mock_send_data:
            sender.send_text(content)
            
            mock_send_data.assert_called_once_with({"content": content})

    @patch('dags.ro_dou_src.notification.notification_sender.apprise.Apprise')
    def test_send_text_with_html_footer(self, mock_apprise_class):
        MockReportConfig = namedtuple(
            "MockReportConfig",
            ["notification", "hide_filters", "header_text", "footer_text", "no_results_found_text"]
        )
        config_with_html_footer = MockReportConfig(
            notification={"serviceId": "discord", "webhookId": "123", "webhookToken": "abc"},
            hide_filters=False,
            header_text=None,
            footer_text="<p>HTML Footer</p>",
            no_results_found_text="No results"
        )
        
        mock_apprise_instance = MagicMock()
        mock_apprise_class.return_value = mock_apprise_instance
        
        sender = NotificationSender(config_with_html_footer)
        content = "Test content"
        
        with patch.object(sender, 'send_data') as mock_send_data:
            sender.send_text(content)
            
            expected_content = content + "HTML Footer" + "\n"
            mock_send_data.assert_called_once_with({"content": expected_content})


class TestNotificationSenderSendEmbeds:
    """Test NotificationSender send_embeds method"""
    
    @patch('dags.ro_dou_src.notification.notification_sender.apprise.Apprise')
    def test_send_embeds_single_item(self, mock_apprise_class, mock_report_config):
        mock_apprise_instance = MagicMock()
        mock_apprise_class.return_value = mock_apprise_instance

        sender = NotificationSender(mock_report_config)
        items = [
            {
                "section": "Seção 3",
                "title": "Test Title",
                "href": "https://example.com",
                "abstract": "Test abstract",
                "date": "01/01/2024"
            }
        ]

        sender.send_embeds(items)

        expected_message = (
            "📁 **Seção 3**\n\n"
            "📅 01/01/2024\n\n"
            "**Test Title**\n\n"
            "Test abstract\n\n"
            "🔗 <https://example.com>\n\n"
            "━━━━━━━━━━━━━━━━━\n\n"
            "Test Footer\n"
        )
        assert sender.payload[0] == expected_message

    @patch('dags.ro_dou_src.notification.notification_sender.apprise.Apprise')
    def test_send_embeds_multiple_items(self, mock_apprise_class, mock_report_config):
        mock_apprise_instance = MagicMock()
        mock_apprise_class.return_value = mock_apprise_instance

        sender = NotificationSender(mock_report_config)
        items = [
            {
                "section": "Seção 1",
                "title": "Title 1",
                "href": "https://example1.com",
                "abstract": "Abstract 1",
                "date": "01/01/2024"
            },
            {
                "section": "Seção 2",
                "title": "Title 2",
                "href": "https://example2.com",
                "abstract": "Abstract 2",
                "date": "02/01/2024"
            }
        ]

        sender.send_embeds(items)

        assert "📁 **Seção 1**" in sender.message
        assert "**Title 1**" in sender.message
        assert "📁 **Seção 2**" in sender.message
        assert "**Title 2**" in sender.message

    @patch('dags.ro_dou_src.notification.notification_sender.apprise.Apprise')
    def test_send_embeds_without_footer(self, mock_apprise_class, mock_report_config_no_header_footer):
        mock_apprise_instance = MagicMock()
        mock_apprise_class.return_value = mock_apprise_instance

        sender = NotificationSender(mock_report_config_no_header_footer)
        items = [
            {
                "section": "Seção 3",
                "title": "Test Title",
                "href": "https://example.com",
                "abstract": "Test abstract",
                "date": "01/01/2024"
            }
        ]

        sender.send_embeds(items)

        expected_message = (
            "📁 **Seção 3**\n\n"
            "📅 01/01/2024\n\n"
            "**Test Title**\n\n"
            "Test abstract\n\n"
            "🔗 <https://example.com>\n\n"
            "━━━━━━━━━━━━━━━━━\n\n"
        )
        assert sender.payload[0] == expected_message


class TestNotificationSenderSendData:
    """Test NotificationSender send_data method"""
    
    @patch('dags.ro_dou_src.notification.notification_sender.apprise.Apprise')
    def test_send_data_discord_service(self, mock_apprise_class, mock_report_config):
        mock_apprise_instance = MagicMock()
        mock_apprise_class.return_value = mock_apprise_instance
        
        sender = NotificationSender(mock_report_config)
        data = "Test notification data"
        
        sender.send_data(data)
        
        expected_notification = {
            "serviceId": "discord://",
            "webhookId": "123456789",
            "webhookToken": "abcdef123"
        }
        mock_apprise_instance.add.assert_called_once_with(expected_notification)
        mock_apprise_instance.notify.assert_called_once_with(body=data)
        
class TestNotificationSenderHelperMethods:
    """Test NotificationSender helper methods"""

    def test_remove_html_tags_simple(self, mock_report_config):
        sender = NotificationSender(mock_report_config)
        
        result = sender._remove_html_tags("<p>Hello <strong>World</strong></p>")
        assert result == "Hello World"

    def test_remove_html_tags_complex(self, mock_report_config):
        sender = NotificationSender(mock_report_config)
        
        html_text = '<div class="content"><h1>Title</h1><p>Text with <a href="link">link</a></p></div>'
        result = sender._remove_html_tags(html_text)
        assert result == "TitleText with link"

    def test_remove_html_tags_none_input(self, mock_report_config):
        sender = NotificationSender(mock_report_config)
        
        result = sender._remove_html_tags(None)
        assert result is None

    def test_remove_html_tags_empty_string(self, mock_report_config):
        sender = NotificationSender(mock_report_config)
        
        result = sender._remove_html_tags("")
        assert result == ""

    def test_remove_html_tags_non_string_input(self, mock_report_config):
        sender = NotificationSender(mock_report_config)
        
        result = sender._remove_html_tags(123)
        assert result == 123


class TestNotificationSenderIntegration:
    """Integration tests for NotificationSender"""
    
    @patch('dags.ro_dou_src.notification.notification_sender.apprise.Apprise')
    def test_full_notification_flow(self, mock_apprise_class, mock_report_config, sample_search_report):
        mock_apprise_instance = MagicMock()
        mock_apprise_class.return_value = mock_apprise_instance
        
        sender = NotificationSender(mock_report_config)
        sender.send(sample_search_report, "2024-04-01")
        
        # Verify notification was sent
        mock_apprise_instance.notify.assert_called()
        
        # Verify message content includes expected elements
        assert "Test Header" in sender.message
        assert "**Seção 3**" in sender.message
        assert "\n\n**Unidade: Department A**\n\n📁 **Seção 3**\n\n" in sender.message
        assert "\n\n**EXTRATO DE COMPROMISSO**\n\n" in sender.message

    @patch('dags.ro_dou_src.notification.notification_sender.apprise.Apprise')
    def test_notification_with_highlighting_placeholders(self, mock_apprise_class, mock_report_config):
        mock_apprise_instance = MagicMock()
        mock_apprise_class.return_value = mock_apprise_instance
        
        report_with_placeholders = [
            {
                "header": "Seção 3",
                "result": {
                    "group_1": {
                        "term_1": {
                            "Department A": [
                                {
                                    "section": "Seção 3",
                                    "title": "Test Title",
                                    "href": "https://example.com",
                                    "abstract": "Text with <%%>highlighted</%> content",
                                    "date": "01/01/2024"
                                }
                            ]
                        }
                    }
                }
            }
        ]
        
        sender = NotificationSender(mock_report_config)
        
        # Test that the parent class highlighting method would be called
        # (NotificationSender doesn't override send_report, so it uses ISender's implementation)
        with patch.object(sender, '_highlighted_reports') as mock_highlight:
            mock_highlight.return_value = report_with_placeholders[0]
            sender.send_report(report_with_placeholders, "2024-04-01")
            mock_highlight.assert_called_once_with(report_with_placeholders[0])

    @patch('dags.ro_dou_src.notification.notification_sender.apprise.Apprise')
    def test_notification_error_handling(self, mock_apprise_class, mock_report_config, sample_search_report):
        mock_apprise_instance = MagicMock()
        mock_apprise_instance.notify.side_effect = Exception("Network error")
        mock_apprise_class.return_value = mock_apprise_instance
        
        sender = NotificationSender(mock_report_config)
        
        # The method should propagate the exception
        with pytest.raises(Exception, match="Network error"):
            sender.send(sample_search_report, "2024-04-01")


class TestNotificationSenderEdgeCases:
    """Test edge cases and error conditions"""
    
    def test_send_with_malformed_search_report(self, mock_report_config):
        sender = NotificationSender(mock_report_config)
        
        # Test with report missing 'result' key
        malformed_report = [{"header": "Test"}]
        
        # Should not raise exception, just process what's available
        sender.send(malformed_report, "2024-04-01")
        assert "**Test**" in sender.message

    def test_send_with_nested_empty_structures(self, mock_report_config):
        sender = NotificationSender(mock_report_config)

        nested_empty_report = [
            {
                "header": "Seção 1",
                "result": {
                    "group_1": {},
                    "group_2": {
                        "term_1": {},
                        "term_2": {
                            "Department A": []
                        }
                    }
                }
            }
        ]

        # Mock the apprise notify to return False (indicating failure)
        with patch.object(sender.apobj, 'notify', return_value=False):
            with pytest.raises(RuntimeError, match="Notification delivery failed"):
                sender.send(nested_empty_report, "2024-04-01")

    def test_highlight_tags_attribute(self, mock_report_config):
        sender = NotificationSender(mock_report_config)
        
        assert hasattr(sender, 'highlight_tags')
        assert sender.highlight_tags == ("__", "__")

    @patch('dags.ro_dou_src.notification.notification_sender.apprise.Apprise')
    def test_send_data_with_different_data_types(self, mock_apprise_class, mock_report_config):
        mock_apprise_instance = MagicMock()
        mock_apprise_class.return_value = mock_apprise_instance
        
        sender = NotificationSender(mock_report_config)
        
        # Test with string data
        sender.send_data("string data")
        mock_apprise_instance.notify.assert_called_with(body="string data")
        
        # Test with dict data
        dict_data = {"content": "dict content"}
        sender.send_data(dict_data)
        mock_apprise_instance.notify.assert_called_with(body=dict_data)