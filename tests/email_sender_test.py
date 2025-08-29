from collections import namedtuple
from unittest.mock import Mock, MagicMock, patch

from bs4 import BeautifulSoup

import pytest
import apprise
from pytest_mock import MockerFixture

from dags.ro_dou_src.notification.email_sender import EmailSender
  
@pytest.fixture
def mock_report_config():
    """Mock ReportConfig for testing"""
    MockReportConfig = namedtuple(
        "MockReportConfig",
        [
            "hide_filters",            
            "header_text",
            "footer_text",
            "no_results_found_text"
        ]
    )
    return MockReportConfig(   
        hide_filters=False,
        header_text="Test Header",
        footer_text="Test Footer", 
        no_results_found_text="Nenhum resultado encontrado"
    )

@pytest.fixture
def mock_report_config_send_email():
    """Mock ReportConfig for testing"""
    MockReportConfig = namedtuple(
        "MockReportConfig",
        [
            "hide_filters",
            "subject",
            "skip_null",
            "emails",
            "attach_csv",
            "header_text",
            "footer_text",
            "no_results_found_text"
        ]
    )
    return MockReportConfig(   
        hide_filters=False,
        subject="Test Subject",
        skip_null=False,
        emails=["teste@gestao.gov.br"],
        attach_csv=False,
        header_text="Test Header",
        footer_text="Test Footer", 
        no_results_found_text="Nenhum resultado encontrado"
    )

class TestEmailSenderInit:
    def test_init_with_valid_config(self, mock_report_config):
        sender = EmailSender(mock_report_config)
        
        assert isinstance(sender.apobj, apprise.Apprise)


class TestEmailSenderProcessing:
    def test_generate_email_content(self, mock_report_config):
        sender = EmailSender(mock_report_config)
       
        sender.search_report = [
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
        
        email_content = sender.generate_email_content()

        soup = BeautifulSoup(email_content, 'html.parser')

        # Procurar por elementos específicos
        h2_element = soup.find('h2')
        p_element = soup.find('p', string='ALESSANDRO GLAUCO DOS ANJOS DE VASCONCELOS - Secretário-Executivo Adjunto...')
        footer_p = soup.find('p', string='Test Footer')
        date_p = soup.find('p', string='02/09/2021')
        
        assert h2_element is not None
        assert h2_element.text == 'Seção 3'
        assert p_element is not None
        assert p_element.text == 'ALESSANDRO GLAUCO DOS ANJOS DE VASCONCELOS - Secretário-Executivo Adjunto...'
        assert footer_p is not None
        assert footer_p.text == 'Test Footer'
        assert date_p is not None

    def test_get_csv_tempfile(self, mock_report_config):
        sender = EmailSender(mock_report_config)
        sender.search_report = [
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
        csv_file = sender.get_csv_tempfile()
        assert csv_file is not None
        assert csv_file.name.endswith('.csv')

    @patch('dags.ro_dou_src.notification.email_sender.apprise.Apprise')
    def test_send_email(self, mock_apprise_class, mock_report_config_send_email):
        mock_apprise_instance = MagicMock()
        mock_apprise_class.return_value = mock_apprise_instance

        sender = EmailSender(mock_report_config_send_email)
        report = [
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
        
        sender.search_report = report
        sender.watermark = "<p>Test Watermark</p>"

        email_content = sender.send(search_report=report, report_date="2024-04-01")
                 
        assert mock_apprise_instance.notify.call_count == 1
        assert email_content is None