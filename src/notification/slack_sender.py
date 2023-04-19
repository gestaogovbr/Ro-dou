from datetime import datetime

import requests

from notification.isender import ISender


class SlackSender(ISender):
    highlight_tags = ('*', '*')

    def __init__(self, specs) -> None:
        self.webhook_url = specs.slack_webhook
        self.blocks = []


    def send(self, search_report: dict, report_date: str=None):
        """Parse the content, and send message to Discord"""
        for group, results in search_report.items():
            if group != 'single_group':
                self._add_header(f'Grupo: {group}')
            for term, items in results.items():
                if items:
                    self._add_header(f'Termo: {term}')
                    for item in items:
                        self._add_block(item)
        self._flush()


    def _add_header(self, text):
        self.blocks.append({
            "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": text,
                    "emoji": True
                }
            })


    def _add_block(self, item):
        self.blocks += [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": item['title']
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": item['abstract']
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"Publicado em: *{_format_date(item['date'])}*"
                },
                "accessory": {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "Acessar publicação",
                        "emoji": True
                    },
                    "value": "click_me_123",
                    "url": item['href'],
                    "action_id": "button-action"
                }
            },
            {
                "type": "divider"
            }
        ]


    def _flush(self):
        for i in range(0, len(self.blocks), 50):
            data = {
                'blocks': self.blocks[i:i + 50]
            }
            result = requests.post(self.webhook_url, json=data)
            result.raise_for_status()


WEEKDAYS_EN_TO_PT = [
    ("Mon", "Seg"),
    ("Tue", "Ter"),
    ("Wed", "Qua"),
    ("Thu", "Qui"),
    ("Fri", "Sex"),
    ("Sat", "Sáb"),
    ("Sun", "Dom")
]

def _format_date(date_str: str) -> str:
    date = datetime.strptime(date_str, "%d/%m/%Y")
    _from, _to = WEEKDAYS_EN_TO_PT[date.weekday()]
    return date.strftime("%a %d/%m").replace(_from, _to)
