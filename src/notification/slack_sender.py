import requests

from notification.isender import ISender


class SlackSender(ISender):

    def __init__(self, specs) -> None:
        self.webhook_url = specs.slack_webhook


    def send(self, search_report: dict, report_date: str=None):
        """Parse the content, and send message to Slack"""
        blocks = []
        for group, results in search_report.items():
            if group != 'single_group':
                blocks.append(f'**Grupo: {group}**\n')
            for term, items in results.items():
                if not items:
                    continue
                blocks.append(f'**Resultados para: {term}**\n')
                for item in items:
                    item_md = f"""
                        ### [{item['title']}]({item['href']})
                        {item['abstract']}
                        {item['date']}"""
                    blocks.append(item_md)

        self._send_to_slack('\n'.join(blocks))


    def _send_to_slack(self, md_text: str):
        data = {
            'text': {
                'type': 'mrkdwn',
                'text': md_text
            }
        }
        result = requests.post(self.webhook_url, json=data)
        result.raise_for_status()
