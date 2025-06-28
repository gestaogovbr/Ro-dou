import re

import requests

from notification.isender import ISender
from schemas import ReportConfig


class DiscordSender(ISender):
    highlight_tags = ("__", "__")

    def __init__(self, report_config: ReportConfig) -> None:
        self.webhook_url = report_config.discord["webhook"]
        self.hide_filters = report_config.hide_filters
        self.header_text = report_config.header_text
        self.footer_text = report_config.footer_text
        self.no_results_found_text = report_config.no_results_found_text

    def send(self, search_report: list, report_date: str = None):
        """Parse the content, and send message to Discord"""
        if self.header_text:
            header_text = self._remove_html_tags(self.header_text)
            self.send_text(header_text)

        for search in search_report:
            if search["header"]:
                self.send_text(f'**{search["header"]}**')

            for group, search_results in search["result"].items():
                if not self.hide_filters:
                    if group != "single_group":
                        self.send_text(f"**Grupo: {group}**")

                for term, term_results in search_results.items():
                    if not self.hide_filters:
                        if not term_results:
                            self.send_text(
                                f"**{self.no_results_found_text}**"
                            )
                        else:
                            self.send_text(f"**Resultados para: {term}**")

                            for department, results in term_results.items():
                                if not self.hide_filters and department != 'single_department':
                                    self.send_text(f"{department}")

                                self.send_embeds(results)

        if self.footer_text:
            footer_text = self._remove_html_tags(self.footer_text)
            self.send_text(footer_text)

    def send_text(self, content):
        self.send_data({"content": content})

    def send_embeds(self, items):
        self.send_data(
            {
                "embeds": [
                    {
                        "title": item["title"],
                        "description": item["abstract"],
                        "url": item["href"],
                    }
                    for item in items
                ]
            }
        )

    def send_data(self, data):
        data["username"] = "Querido Prisma (rodou)"
        result = requests.post(self.webhook_url, json=data)
        result.raise_for_status()

    def _remove_html_tags(self, text):
        # Define a regular expression pattern to match HTML tags
        clean = re.compile('<.*?>')
        # Substitute HTML tags with an empty string
        return re.sub(clean, '', text)
