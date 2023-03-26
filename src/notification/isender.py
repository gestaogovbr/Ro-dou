import copy
from abc import ABC, abstractmethod


class ISender(ABC):
    """Interface that defines a notifier sender.
    """
    @abstractmethod
    def send(self, search_report: dict, report_date: str=None):
        """Implement this method sending the report to destination
        according to its API!

        Args:
            search_report (dict): A dictionary containing the search results.
            report_date (str, optional): The date of the search report. Defaults to None.
        """
        pass


    def send_report(self, search_report: dict, report_date: str=None):
        """Send a notification with the search report, after highlighting the abstracts.

        Args:
            search_report (dict): A dictionary containing the search results.
            report_date (str, optional): The date of the search report. Defaults to None.
        """
        search_report = self._highlighted_reports(search_report)
        self.send(search_report, report_date)


    def _highlighted_reports(self, search_report) -> dict:
        """Replace placeholders with specific formatting depending on
        the sender type.

        Args:
            search_report (dict): A dictionary containing the search results.

        Returns:
            dict: A dictionary with the placeholders replaced with formatting tags.
        """
        reports = copy.deepcopy(search_report)
        for _, results in reports.items():
            for _, items in results.items():
                for item in items:
                    open_tag, close_tag = self.highlight_tags
                    item['abstract'] = item['abstract'] \
                        .replace('<%%>', open_tag) \
                        .replace('</%%>', close_tag)

        return reports
