import requests


class DiscordSender:

    def __init__(self, webhook_url: str) -> None:
        self.webhook_url = webhook_url



    def send_text_to_discord(self, content):
        self.send_discord_data({ "content" : content })


    def send_discord_data(self, data):
        data['username'] = 'Querido Prisma (rodou)'
        result = requests.post(self.webhook_url, json=data)
        result.raise_for_status()
