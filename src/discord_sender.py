import ast

import requests


class DiscordSender:

    def __init__(self, webhook_url: str) -> None:
        self.webhook_url = webhook_url


    def send_discord(self, search_report: str):
        obj_results = ast.literal_eval(search_report)

        self._send_discord(obj_results)


    def _send_discord(self, search_report: list):
        """Parse the content, and send message to Discord"""
        for group, results in search_report.items():
            if group != 'single_group':
                self.send_text_to_discord(f'**Grupo: {group}**')
            for term, items in results.items():
                if items:
                    self.send_text_to_discord(f'**Resultados para: {term}**')
                self.send_embeds_to_discord(items)


    def send_text_to_discord(self, content):
        self.send_discord_data({ "content" : content })


    def send_embeds_to_discord(self, items):
        self.send_discord_data(
            {
                "embeds" :  [
                    {
                        'title': item['title'],
                        'description':item['abstract'],
                        'url': item['href'],
                    }
                    for item in items
                ]
            })


    def send_discord_data(self, data):
        data['username'] = 'Querido Prisma (rodou)'
        result = requests.post(self.webhook_url, json=data)
        result.raise_for_status()
