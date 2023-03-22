import ast
import os
import sys

# TODO fix this
# Add parent folder to sys.path in order to be able to import
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from notification.discord_sender import DiscordSender
from notification.email_sender import EmailSender
from parsers import DAGConfig


class Notifier:
    """Performs the notification delivery through different means as
    defined in the YAML file. Currently it sends notification to email
    and Discord.
    """

    def __init__(self, specs: DAGConfig) -> None:
        self.specs = specs


    def send_notification(self, search_report: str, report_date: str):
        # Convert to data structure after it's retrieved from xcom
        search_report = ast.literal_eval(search_report)
        if self.specs.discord_webhook:
            DiscordSender(self.specs).send_discord(search_report)
        else:
            EmailSender(self.specs).send_email(search_report, report_date)
