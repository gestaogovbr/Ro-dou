import apprise

from notification.isender import ISender
from schemas import ReportConfig

import re


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
        self.payload = []
        self.delimiter = "━━━━━━━━━━━━━━━━━"

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

        # Finally, send the accumulated data
        message_payload = "\n".join(self.payload)
        self.send_chunked(message_payload)

    def _process_search_section(self, search: dict):
        """
        Process a single search section.

        Args:
            search: Dictionary containing 'header' and 'result' keys
        """
        # Send section header
        if search.get("header"):
            self.message += f'{search["header"]}\n'

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
            self.send_text(f"Grupo: {group_name}")

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
                self.message += f"{self.no_results_found_text}"
                self.send_text(self.message)
                return

            # Send term header if not the default term
            if term != "all_publications":
                self.message += f"Resultados para: {term}\n\n"

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
        if not self.hide_filters and department != "single_department":
            self.message += f"Unidade: {department}\n\n"

        # Send the actual results
        self.send_embeds(results)

    def send_text(self, content):
        if self.footer_text:
            footer_text = self._remove_html_tags(self.footer_text)
            content += footer_text + "\n"

        self.send_data({"content": content})

    def send_embeds(self, items):
        self.message += "\n".join(
            f"📁 {item['section']}\n\n"
            f"📅 {item['date']}\n\n"
            f"{item['title']}\n\n"
            f"{item['abstract']}\n\n"
            f"🔗 {item['href']}\n\n" + self.delimiter + "\n\n"
            for item in items
        )

        if self.footer_text:
            footer_text = self._remove_html_tags(self.footer_text)
            self.message += footer_text + "\n"

        self.payload.append(self.message)

    def send_data(self, data):
        """
        Send notification data using Apprise.

        Args:
            data: Data to send (can be string or dict)
        """

        url = self.notification
        self.apobj.add(url)
        self.apobj.notify(body=data)

    def _notify_or_fail(self, content: str):
        sent = self.apobj.notify(body=content)

        if not sent:
            raise RuntimeError("Notification delivery failed")

    def send_chunked(self, message, max_len=1500):

        url = self.notification
        self.apobj.add(url)

        blocks = [
            b + self.delimiter for b in message.split(self.delimiter) if b.strip()
        ]

        current_chunk = ""
        try:
            for block in blocks:

                # If a single block is too large, send it alone
                if len(block) > max_len:
                    if current_chunk:
                        self._notify_or_fail(current_chunk.strip())
                        current_chunk = ""

                    self._notify_or_fail(block.strip())
                    continue

                # Check if block fits in current chunk
                if len(current_chunk) + len(block) > max_len:
                    self._notify_or_fail(current_chunk.strip())
                    current_chunk = block
                else:
                    current_chunk += block

            # Send remaining content
            if current_chunk.strip():
                self._notify_or_fail(current_chunk.strip())

        except Exception:
            raise

    def _remove_html_tags(self, text):
        if not text or not isinstance(text, str):
            return text

        # Remove todas as tags HTML
        text = re.sub(r"<[^>]+>", "", text)
        return text
