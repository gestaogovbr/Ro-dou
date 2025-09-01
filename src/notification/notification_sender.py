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
        self.message = ""

    def send(self, search_report: list, report_date: str = None):
        """
        Parse the content and send message to client.
        
        Args:
            search_report: List of search results containing headers and results
            report_date: Optional date for the report (currently unused)
        """
        # Check if search_report is empty
        if not search_report:
            return

        # Send header if exists
        if self.header_text:
            header_text = self._remove_html_tags(self.header_text)
            self.message += header_text + "\n"
        
        # Process each search in the report
        for search in search_report:
            self._process_search_section(search)
        
    def _process_search_section(self, search: dict):
        """
        Process a single search section.
        
        Args:
            search: Dictionary containing 'header' and 'result' keys
        """
        # Send section header
        if search.get("header"):
            self.message += f'**{search["header"]}**' + "\n"
        
        # Process all groups in this search
        for group_name, search_results in search.get("result", {}).items():
            self._process_group(group_name, search_results)

    def _process_group(self, group_name: str, search_results: dict):
        """
        Process a single group of search results.
        
        Args:
            group_name: Name of the group
            search_results: Dictionary of term results
        """
        # Send group header if not hiding filters and not default group
        if not self.hide_filters and group_name != "single_group":
            self.send_text(f"**Grupo: {group_name}**")
        
        # Process each term in the group
        for term, term_results in search_results.items():
            self._process_term_results(term, term_results)

    def _process_term_results(self, term: str, term_results: dict):
        """
        Process results for a specific search term.
        
        Args:
            term: Search term
            term_results: Dictionary of department results
        """        
        if not self.hide_filters:
            if not term_results:                
                # self.message += f'**{search["header"]}**' + "\n"
                self.message += f"**{self.no_results_found_text}**"
                self.send_text(self.message)
                return
            
            # Send term header if not the default term
            if term != "all_publications":
                self.message += f"**Resultados para: {term}**\n"               
        
        # Process results by department
        for department, results in term_results.items():
            self._process_department_results(department, results)

    def _process_department_results(self, department: str, results):
        """
        Process results for a specific department.
        
        Args:
            department: Department name
            results: Results to send as embeds
        """
        # Send department name if not hiding filters and not default department
        if not self.hide_filters and department != 'single_department':
            self.message += f"**Departamento: {department}**\n"           

        # Send the actual results
        self.send_embeds(results)

    def send_text(self, content):           
        if self.footer_text:
            footer_text = self._remove_html_tags(self.footer_text)
            content += footer_text + "\n"
             
        self.send_data({"content": content})

    def send_embeds(self, items):         

        self.message += "\n".join(
            [
                f"*📁 {item['section']}*\n*📋 {item['title']}*\n{item['abstract']}\n 🔗 {item['href']}\n 📅 {item['date']}\n"
                for item in items
            ]
        )

        if self.footer_text:
            footer_text = self._remove_html_tags(self.footer_text)
            self.message += footer_text + "\n"

        self.send_data(self.message)
       
    def send_data(self, data):
        serviceId = self._remove_tag_from_serviceId(self.notification['serviceId'])        
        url = f"{serviceId}://{self.notification['webhookId']}/{self.notification['webhookToken']}"        
        self.apobj.add(url)               

        self.apobj.notify(body=data)

    def _remove_tag_from_serviceId(self, text):
        padrao = r"://"
        if re.search(padrao, text):
            text = re.sub(padrao, "", text)
        return text

    def _remove_html_tags(self, text):
        if not text or not isinstance(text, str):
            return text

        # Remove todas as tags HTML
        text = re.sub(r'<[^>]+>', '', text)
        return text     
