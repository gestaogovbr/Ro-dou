"""Send reports to Slack.
"""

from datetime import datetime
import re

import requests
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
                        if not self.hide_filters:
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

    def _flush(self):
        for i in range(0, len(self.blocks), 50):
            data = {"blocks": self.blocks[i : i + 50]}
            result = requests.post(self.webhook_url, json=data)
            result.raise_for_status()


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
