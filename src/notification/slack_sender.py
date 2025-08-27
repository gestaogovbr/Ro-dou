"""Send reports to Slack.
"""

from datetime import datetime
import re

import requests
import apprise
from notification.isender import ISender

from schemas import ReportConfig


class SlackSender(ISender):
    """Prepare a report and send it to Slack.
    """
    highlight_tags = ("*", "*")

    def __init__(self, report_config: ReportConfig) -> None:
        self.webhook_url = report_config.slack["webhook"]
        self.blocks = []
        self.hide_filters = report_config.hide_filters
        self.header_text = report_config.header_text
        self.footer_text = report_config.footer_text
        self.no_results_found_text = report_config.no_results_found_text
        self.apobj = apprise.Apprise()

    def send(self, search_report: list, report_date: str = None):
        """Parse the content, and send message to Slack"""
        if self.header_text:
            header_text = _remove_html_tags(self.header_text)
            self._add_header(header_text)

        for search in search_report:
            if search["header"]:
                self._add_header(search["header"])

            for group, search_results in search["result"].items():
                if not self.hide_filters:
                    if group != "single_group":
                        self._add_header(f"Grupo: {group}")

                for term, term_results in search_results.items():
                    if not term_results:
                        self._add_text(
                            self.no_results_found_text
                        )
                    else:
                        if not self.hide_filters and term != "all_publications":
                            self._add_header(f"Termo: {term}")

                        for department, results in term_results.items():
                            if not self.hide_filters and department != 'single_department':
                                self._add_header(f"{department}")

                            for result in results:
                                self._add_block(result)

        if self.footer_text:
            footer_text = _remove_html_tags(self.footer_text)
            self._add_header(footer_text)
        self._flush()

    def _add_header(self, text):
        self.blocks.append(
            {
                "type": "header",
                "text": {"type": "plain_text", "text": text, "emoji": True},
            }
        )

    def _add_text(self, text):
        self.blocks += [
            {
                "type": "section",
                "text": {"type": "plain_text", "text": text, "emoji": True},
            },
            {"type": "divider"},
        ]

    def _add_block(self, item):
        self.blocks += [
            {"type": "section", "text": {"type": "mrkdwn", "text": item["title"]}},
            {"type": "section", "text": {"type": "mrkdwn", "text": item["abstract"]}},
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"Publicado em: *{_format_date(item['date'])}*",
                },
                "accessory": {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "Acessar publicação",
                        "emoji": True,
                    },
                    "value": "click_me_123",
                    "url": item["href"],
                    "action_id": "button-action",
                },
            },
            {"type": "divider"},
        ]

    def _convert_dou_data_to_apprise(self, data):
        """
        Converte dados do DOU para formato texto simples do Apprise
        """

        message_parts = []
        blocks = data.get('blocks', [])
        
        current_publication = {}
        
        for block in blocks:
            block_type = block.get('type')
            
            if block_type == 'header':
                # Headers são títulos/seções
                text = block['text']['text']
                message_parts.append(f"📋 *{text}*")
                message_parts.append("")
                
            elif block_type == 'section':
                text_content = block.get('text', {}).get('text')
                
                # Pular blocos com texto None
                if text_content is None:
                    continue
                    
                # Se tem accessory (botão), é a última parte de uma publicação
                if 'accessory' in block and block['accessory'].get('type') == 'button':
                    # É a data + botão, última parte da publicação
                    date_text = text_content
                    button_url = block['accessory']['url']
                    
                    message_parts.append(date_text)
                    message_parts.append(f"🔗 {button_url}")
                    
                else:
                    # É título ou abstract de publicação
                    if text_content.strip():
                        # Se parece com título (mais curto, sem "(...)")
                        if len(text_content) < 100 and not text_content.startswith('(...)'):
                            message_parts.append(f"📄 *{text_content.strip()}*")
                        else:
                            # É abstract
                            # Limitar tamanho para não ficar muito longo
                            if len(text_content) > 400:
                                text_content = text_content[:400] + "..."
                            message_parts.append(text_content)
                            
            elif block_type == 'divider':
                # Separador entre publicações
                message_parts.append("─" * 50)
                message_parts.append("")
        
        return '\n'.join(message_parts)

    def _flush(self):
        for i in range(0, len(self.blocks), 50):
            data = {"blocks": self.blocks[i : i + 50]}
            self.apobj.add(self.webhook_url)           
            message = self._convert_dou_data_to_apprise(data)
            title = self._remove_html_tags(self.header_text)
            self.apobj.notify(body=message if message else self.no_results_found_text, title= title if title else "Nova Notificação")



WEEKDAYS_EN_TO_PT = [
    ("Mon", "Seg"),
    ("Tue", "Ter"),
    ("Wed", "Qua"),
    ("Thu", "Qui"),
    ("Fri", "Sex"),
    ("Sat", "Sáb"),
    ("Sun", "Dom"),
]


def _format_date(date_str: str) -> str:
    date = datetime.strptime(date_str, "%d/%m/%Y")
    _from, _to = WEEKDAYS_EN_TO_PT[date.weekday()]
    return date.strftime("%a %d/%m").replace(_from, _to)


def _remove_html_tags(text):
    # Define a regular expression pattern to match HTML tags
    clean = re.compile("<.*?>")
    # Substitute HTML tags with an empty string
    return re.sub(clean, "", text)
