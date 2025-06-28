import ast
import os
import sys

# TODO fix this
# Add parent folder to sys.path in order to be able to import
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from typing import List

from notification.discord_sender import DiscordSender
from notification.email_sender import EmailSender
from notification.isender import ISender
from notification.slack_sender import SlackSender
from parsers import DAGConfig


class Notifier:
    """Performs the notification delivery through different means as
    defined in the YAML file. Currently it sends notification to email,
    Discord and Slack.
    """
    senders = List[ISender]

    def __init__(self, specs: DAGConfig) -> None:
        self.senders = []
        if specs.report.emails:
            self.senders.append(EmailSender(specs.report))
        if specs.report.discord:
            self.senders.append(DiscordSender(specs.report))
        if specs.report.slack:
            self.senders.append(SlackSender(specs.report))


    def send_notification(self, search_report: str, report_date: str):
        """Sends the notification to the specified email, Discord or Slack

        Args:
            search_report (str): The report to be sent
            report_date (str): The date of the report
        """

        for sender in self.senders:
            sender.send_report(search_report, report_date)
