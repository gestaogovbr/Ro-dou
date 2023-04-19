import requests

from notification.isender import ISender


class DiscordSender(ISender):
    highlight_tags = ('__', '__')

    def __init__(self, specs) -> None:
        self.webhook_url = specs.discord_webhook


    def send(self, search_report: dict, report_date: str=None):
        """Parse the content, and send message to Discord"""
        for group, results in search_report.items():
            if group != 'single_group':
                self.send_text(f'**Grupo: {group}**')
            for term, items in results.items():
                if items:
                    self.send_text(f'**Resultados para: {term}**')
                self.send_embeds(items)


    def send_text(self, content):
        self.send_data({ "content" : content })


    def send_embeds(self, items):
        self.send_data(
            {
                "embeds" :  [
                    {
                        'title': item['title'],
                        'description': item['abstract'],
                        'url': item['href'],
                    }
                    for item in items
                ]
            })


    def send_data(self, data):
        data['username'] = 'Querido Prisma (rodou)'
        result = requests.post(self.webhook_url, json=data)
        result.raise_for_status()
