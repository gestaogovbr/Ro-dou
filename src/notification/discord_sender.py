import requests
import re
from notification.isender import ISender


class DiscordSender(ISender):
    highlight_tags = ("__", "__")

    def __init__(self, specs) -> None:
        self.webhook_url = specs.discord_webhook
        self.hide_filters = specs.hide_filters
        self.header_text = specs.header_text
        self.footer_text = specs.footer_text
        self.no_results_found_text = specs.no_results_found_text

    def send(self, search_report: list, report_date: str = None):
        """Parse the content, and send message to Discord"""
        if self.header_text:
            header_text = self._remove_html_tags(self.header_text)
            self.send_text(header_text)

        for search in search_report:
            if search["header"]:
                self.send_text(f'**{search["header"]}**')

            for group, results in search["result"].items():
                if results:
                    if not self.hide_filters:
                        if group != "single_group":
                            self.send_text(f"**Grupo: {group}**")
                    for term, items in results.items():
                        if not self.hide_filters:
                            if items:
                                self.send_text(f"**Resultados para: {term}**")
                        self.send_embeds(items)
                else:
                    self.send_text(
                        f"**{self.no_results_found_text}**"
                    )

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