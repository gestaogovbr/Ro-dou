import os
import sys

# Add parent folder to sys.path in order to be able to import
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from typing import List, Optional

from notification.discord_sender import DiscordSender
from notification.email_sender import EmailSender
from notification.isender import ISender
from notification.slack_sender import SlackSender
from parsers import DAGConfig

_SENDER_CLASSES = {
    "email": ("emails", EmailSender),
    "discord": ("discord", DiscordSender),
    "slack": ("slack", SlackSender),
}


class Notifier:
    """Performs the notification delivery through different means as
    defined in the YAML file. Currently it sends notification to email,
    Discord and Slack.

    Pass `channel` to restrict delivery to a single channel (e.g. "slack"),
    so each channel can be retried independently by Airflow without
    resending to channels that already succeeded.
    """

    senders: List[ISender]

    def __init__(self, specs: DAGConfig, channel: Optional[str] = None) -> None:
        self.senders = []
        channel_names = [channel] if channel else _SENDER_CLASSES.keys()
        for name in channel_names:
            report_attr, sender_class = _SENDER_CLASSES[name]
            if getattr(specs.report, report_attr, None):
                self.senders.append(sender_class(specs.report))

    def send_notification(self, search_report: List[str], report_date: str):
        """Sends the notification to the specified email, Discord, Slack and nother notification services.

        Args:
            search_report (List[str]): The report to be sent
            report_date (str): The date of the report
        """

        for sender in self.senders:
            sender.send_report(search_report, report_date)
