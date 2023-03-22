from abc import ABC, abstractmethod


class ISender(ABC):
    """Interface that defines a notifier sender.
    """
    @abstractmethod
    def send(self, search_report: dict, report_date: str=None):
        pass
