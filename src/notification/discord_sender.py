import requests

from notification.isender import ISender


class DiscordSender(ISender):
    highlight_tags = ("__", "__")

    def __init__(self, specs) -> None:
        self.webhook_url = specs.discord_webhook
        self.hide_filters = specs.hide_filters

    def send(self, search_report: list, report_date: str = None):
        """Parse the content, and send message to Discord"""
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
                        "**Nenhum dos termos pesquisados foi encontrado nesta consulta**"
                    )

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
