import copy
import re
from abc import ABC, abstractmethod

START_PLACEHOLDER_REGEX = re.compile(r"(?<!\s)<%%>")
END_PLACEHOLDER_REGEX = re.compile(r"</%%>(?!\s)")

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
                    item['abstract'] = _fix_missing_spaces(item['abstract']) \
                        .replace('<%%>', open_tag) \
                        .replace('</%%>', close_tag)

        return reports


def _fix_missing_spaces(string: str) -> str:
    """Add missing spaces around placeholders in a string.

    Args:
        string (str): The string to modify.

    Returns:
        str: The modified string with spaces added around the placeholders.
    """
    new_string = START_PLACEHOLDER_REGEX.sub(" <%%>", string)
    new_string = END_PLACEHOLDER_REGEX.sub("</%%> ", new_string)
    return new_string
