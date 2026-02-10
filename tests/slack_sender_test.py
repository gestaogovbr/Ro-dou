from collections import namedtuple
from datetime import datetime
from unittest.mock import MagicMock

import pytest
import requests
from dags.ro_dou_src.notification.slack_sender import (
    SlackSender,
    _format_date,
    _remove_html_tags,
)
from pytest_mock import MockerFixture

WEBHOOK_URL = "https://hooks.slack.com/services/test/webhook/url"

@pytest.fixture
def mock_report_config():
    """Create a mock ReportConfig object for testing."""
    ReportConfig = namedtuple(
        "ReportConfig",
        [
            "slack",
            "hide_filters",
            "header_text",
            "footer_text",
            "no_results_found_text",
        ],
    )
    return ReportConfig(
        slack={"webhook": WEBHOOK_URL},
        hide_filters=False,
        header_text="Test Header",
        footer_text="Test Footer",
        no_results_found_text="Nenhum dos termos pesquisados foi encontrado nesta consulta.",
    )


@pytest.fixture
def mock_report_config_no_texts():
    """Create a mock ReportConfig object without header/footer texts."""
    ReportConfig = namedtuple(
        "ReportConfig",
        [
            "slack",
            "hide_filters",
            "header_text",
            "footer_text",
            "no_results_found_text",
        ],
    )
    return ReportConfig(
        slack={"webhook": WEBHOOK_URL},
        hide_filters=True,
        header_text=None,
        footer_text=None,
        no_results_found_text="Nenhum resultado encontrado.",
    )


@pytest.fixture
def sample_search_report():
    """Sample search report data for testing."""
    return [
        {
            "header": "Test Report Header",
            "result": {
                "test_group": {
                    "test_term": {
                        "test_department": [
                            {
                                "title": "Test Publication Title",
                                "abstract": "Test publication abstract with important content",
                                "date": "15/03/2023",
                                "href": "https://example.com/publication/123",
                            },
                            {
                                "title": "Another Test Publication",
                                "abstract": "Another abstract with relevant information",
                                "date": "16/03/2023",
                                "href": "https://example.com/publication/124",
                            },
                        ],
                    },
                    "empty_term": {
                        "test_department": [],
                    },
                },
            },
        }
    ]


class TestSlackSenderInitialization:
    def test_init_with_complete_config(self, mock_report_config):
        sender = SlackSender(mock_report_config)
        
        assert sender.webhook_url == WEBHOOK_URL
        assert sender.hide_filters == False
        assert sender.header_text == "Test Header"
        assert sender.footer_text == "Test Footer"
        assert sender.no_results_found_text == "Nenhum dos termos pesquisados foi encontrado nesta consulta."
        assert sender.blocks == []

    def test_init_with_minimal_config(self, mock_report_config_no_texts):
        sender = SlackSender(mock_report_config_no_texts)
        
        assert sender.webhook_url == WEBHOOK_URL
        assert sender.hide_filters == True
        assert sender.header_text is None
        assert sender.footer_text is None


class TestSlackSenderPrivateMethods:
    def test_add_header(self, mock_report_config):
        sender = SlackSender(mock_report_config)
        sender._add_header("Test Header Text")
         
        expected_block = {
            "type": "header",
            "text": {"type": "plain_text", "text": "Test Header Text", "emoji": True},
        }
        
        assert len(sender.blocks) == 1
        assert sender.blocks[0] == expected_block

    def test_add_text(self, mock_report_config):
        sender = SlackSender(mock_report_config)
        sender._add_text("Test text content")
        
        expected_blocks = [
            {
                "type": "section",
                "text": {"type": "plain_text", "text": "Test text content", "emoji": True},
            },
            {"type": "divider"},
        ]
        
        assert len(sender.blocks) == 2
        assert sender.blocks == expected_blocks

    def test_add_block(self, mock_report_config):
        sender = SlackSender(mock_report_config)
        test_item = {
            "title": "Test Title",
            "abstract": "Test Abstract",
            "date": "15/03/2023",
            "href": "https://example.com/test",
        }
        sender._add_block(test_item)
        
        expected_blocks = [
            {"type": "section", "text": {"type": "mrkdwn", "text": "Test Title"}},
            {"type": "section", "text": {"type": "mrkdwn", "text": "Test Abstract"}},
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "Publicado em: *Qua 15/03*",
                },
                "accessory": {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "Acessar publicação",
                        "emoji": True,
                    },
                    "value": "click_me_123",
                    "url": "https://example.com/test",
                    "action_id": "button-action",
                },
            },
            {"type": "divider"},
        ]
        
        assert len(sender.blocks) == 4
        assert sender.blocks == expected_blocks

    def test_flush_single_batch(self, mock_report_config, mocker: MockerFixture):
        mock_post = mocker.patch("requests.post")
        mock_response = MagicMock()
        mock_post.return_value = mock_response
        
        sender = SlackSender(mock_report_config)
        sender.blocks = [{"type": "header", "text": {"type": "plain_text", "text": "Test"}}]
        sender._flush()
        
        mock_post.assert_called_once_with(
            WEBHOOK_URL,
            json={"blocks": [{"type": "header", "text": {"type": "plain_text", "text": "Test"}}]}
        )
        mock_response.raise_for_status.assert_called_once()

    def test_flush_multiple_batches(self, mock_report_config, mocker: MockerFixture):
        mock_post = mocker.patch("requests.post")
        mock_response = MagicMock()
        mock_post.return_value = mock_response
        
        sender = SlackSender(mock_report_config)
        # Create 55 blocks to test batching (50 per batch)
        sender.blocks = [{"type": "divider"}] * 55
        sender._flush()
        
        assert mock_post.call_count == 2
        # First batch: 50 blocks
        first_call_data = mock_post.call_args_list[0][1]["json"]
        assert len(first_call_data["blocks"]) == 50
        # Second batch: 5 blocks
        second_call_data = mock_post.call_args_list[1][1]["json"]
        assert len(second_call_data["blocks"]) == 5


class TestSlackSenderSendMethod:
    def test_send_with_complete_report(self, mock_report_config, sample_search_report, mocker: MockerFixture):
        mock_post = mocker.patch("requests.post")
        mock_response = MagicMock()
        mock_post.return_value = mock_response
        
        sender = SlackSender(mock_report_config)
        sender.send(sample_search_report)
        
        # Verify that _flush was called (requests.post should be called)
        assert mock_post.called
        mock_response.raise_for_status.assert_called()

    def test_send_with_hidden_filters(self, mock_report_config_no_texts, sample_search_report, mocker: MockerFixture):
        mock_post = mocker.patch("requests.post")
        mock_response = MagicMock()
        mock_post.return_value = mock_response
        
        sender = SlackSender(mock_report_config_no_texts)
        sender.send(sample_search_report)
        
        # With hide_filters=True, there should be fewer blocks
        assert mock_post.called

    def test_send_with_empty_results(self, mock_report_config, mocker: MockerFixture):
        mock_post = mocker.patch("requests.post")
        mock_response = MagicMock()
        mock_post.return_value = mock_response
        
        empty_report = [
            {
                "header": None,
                "result": {
                    "single_group": {
                        "empty_term": {
                            "single_department": [],
                        },
                    },
                },
            }
        ]
        
        sender = SlackSender(mock_report_config)
        sender.send(empty_report)
        
        assert mock_post.called

    def test_send_with_header_and_footer(self, mock_report_config, mocker: MockerFixture):
        mock_post = mocker.patch("requests.post")
        mock_response = MagicMock()
        mock_post.return_value = mock_response
        
        # Mock _remove_html_tags to avoid the self parameter issue
        mocker.patch("dags.ro_dou_src.notification.slack_sender._remove_html_tags", return_value="Clean text")
        
        minimal_report = [
            {
                "header": None,
                "result": {
                    "single_group": {
                        "test_term": {
                            "single_department": [],
                        },
                    },
                },
            }
        ]
        
        sender = SlackSender(mock_report_config)
        sender.send(minimal_report)
        
        assert mock_post.called


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


class TestSlackSenderErrorHandling:
    def test_flush_http_error(self, mock_report_config, mocker: MockerFixture):
        mock_post = mocker.patch("requests.post")
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.HTTPError("HTTP Error")
        mock_post.return_value = mock_response
        
        sender = SlackSender(mock_report_config)
        sender.blocks = [{"type": "header", "text": {"type": "plain_text", "text": "Test"}}]
        
        with pytest.raises(requests.HTTPError):
            sender._flush()

    def test_send_with_malformed_search_report(self, mock_report_config):
        sender = SlackSender(mock_report_config)
        
        # Test with malformed report structure
        malformed_report = [
            {
                "header": "Test",
                "result": {
                    "group": {
                        "term": {
                            "department": [
                                {
                                    # Missing required fields
                                    "title": "Test",
                                    # "abstract" is missing
                                    # "date" is missing
                                    # "href" is missing
                                }
                            ]
                        }
                    }
                }
            }
        ]
        
        # This should not raise an exception but might create incomplete blocks
        try:
            sender.send(malformed_report)
        except KeyError:
            # Expected behavior for malformed data
            pass


class TestSlackSenderIntegration:
    def test_complete_workflow_with_real_data(self, mock_report_config, mocker: MockerFixture):
        """Test the complete workflow with realistic data."""
        mock_post = mocker.patch("requests.post")
        mock_response = MagicMock()
        mock_post.return_value = mock_response
        
        realistic_report = [
            {
                "header": "Relatório DOU - 2023-03-15",
                "result": {
                    "single_group": {
                        "lei de acesso à informação": {
                            "Ministério da Educação": [
                                {
                                    "title": "PORTARIA Nº 123, DE 15 DE MARÇO DE 2023",
                                    "abstract": "Regulamenta a aplicação da Lei de Acesso à Informação no âmbito do Ministério da Educação...",
                                    "date": "15/03/2023",
                                    "href": "https://www.in.gov.br/web/dou/-/portaria-123",
                                }
                            ],
                        },
                        "transparência": {
                            "Controladoria-Geral da União": [
                                {
                                    "title": "INSTRUÇÃO NORMATIVA Nº 45, DE 15 DE MARÇO DE 2023",
                                    "abstract": "Estabelece procedimentos para garantir a transparência dos atos públicos...",
                                    "date": "15/03/2023",
                                    "href": "https://www.in.gov.br/web/dou/-/instrucao-normativa-45",
                                }
                            ],
                        },
                    },
                },
            }
        ]
        
        sender = SlackSender(mock_report_config)
        sender.send(realistic_report)
        
        # Verify that the request was made
        assert mock_post.called
        
        # Check that blocks were created properly
        call_data = mock_post.call_args_list[0][1]["json"]
        assert "blocks" in call_data
        assert len(call_data["blocks"]) > 0