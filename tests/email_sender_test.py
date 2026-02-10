from collections import namedtuple
from unittest.mock import patch

from bs4 import BeautifulSoup

import pytest
import apprise

from dags.ro_dou_src.notification.email_sender import EmailSender

from notification.isender import ISender

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
      
        assert isinstance(sender, ISender)


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
        
        email_content = sender._generate_email_content()

        soup = BeautifulSoup(email_content, 'html.parser')

        # Procurar por elementos específicos
        abstract = soup.find("div", class_="abstract")
        date = soup.find('div', string='02/09/2021') 
        footer = soup.find('div', class_='ext_footer')
        
        assert abstract is not None
        assert abstract.text == 'ALESSANDRO GLAUCO DOS ANJOS DE VASCONCELOS - Secretário-Executivo Adjunto...'
        assert date is not None
        assert date.text == '02/09/2021'
        assert footer is not None

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

    @patch('dags.ro_dou_src.notification.email_sender.send_email')
    def test_send_email(self, mock_send_email, mock_report_config_send_email):
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

        result = sender.send(search_report=report, report_date="2024-04-01")

        # Verifica que send_email foi chamado exatamente 1 vez
        assert mock_send_email.call_count == 1

        # Verifica os argumentos da chamada
        call_args = mock_send_email.call_args
        assert call_args[1]['to'] == ["teste@gestao.gov.br"]
        assert "Test Subject - DOs de 2024-04-01" == call_args[1]['subject']
        assert 'html_content' in call_args[1]
        assert call_args[1]['mime_charset'] == 'utf-8'

        # O método send não retorna nada quando envia o email
        assert result is None