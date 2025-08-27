import re

import requests
import apprise

from notification.isender import ISender
from schemas import ReportConfig


class NotificationSender(ISender):
    highlight_tags = ("__", "__")

    def __init__(self, report_config: ReportConfig) -> None:
        self.notification = report_config.notification
        self.hide_filters = report_config.hide_filters
        self.header_text = report_config.header_text
        self.footer_text = report_config.footer_text
        self.no_results_found_text = report_config.no_results_found_text
        self.apobj = apprise.Apprise()

    def send(self, search_report: list, report_date: str = None):
        """Parse the content, and send message to client"""
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
                            if term != "all_publications":
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

    def _convert_dou_data_to_apprise(self, data):
        """
        Converte dados do DOU para formato texto simples do Apprise
        """      

        message_parts = []
        embeds = data.get('embeds', [])

        if embeds:
            for block in embeds:
                title = block.get('title')

                if title:
                    message_parts.append(f"📋 *{title}*")
                    message_parts.append("")
                
                if block.get('description'):
                    message_parts.append(block.get('description'))

                if block.get('url'):
                    button_url = block.get('url')
                    message_parts.append(f"🔗 {button_url}")
                    message_parts.append("")

        if data.get('content'):
            message_parts.append(data.get('content'))
            message_parts.append("")

        return '\n'.join(message_parts)

    def send_data(self, data):
        serviceId = self._remove_tag_from_serviceId(self.notification['serviceId'])        
        url = f"{serviceId}://{self.notification['webhookId']}/{self.notification['webhookToken']}"        
        self.apobj.add(url)               
        message = self._convert_dou_data_to_apprise(data)           
        title = self._remove_html_tags(self.header_text)

        self.apobj.notify(
            body=message, 
            title=title if title else "Nova Notificação")

    def _remove_tag_from_serviceId(self, text):
        padrao = r"://"
        if re.search(padrao, text):
            text = re.sub(padrao, "", text)
        return text

    def _remove_html_tags(self, text):
        clean = re.compile('<.*?>')
        return re.sub(clean, '', text)
