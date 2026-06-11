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
from notification.notification_sender import NotificationSender
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
        if specs.report.notification:
            self.senders.append(NotificationSender(specs.report))

    def send_notification(
        self,
        search_report: list,
        report_date: str,
        skip_senders: set = None,
    ) -> tuple[set, dict]:
        """Sends the notification to each configured channel independently.

        Returns a tuple of (succeeded_sender_names, {failed_sender_name: exception}).
        Raises RuntimeError at the end if any sender failed, so callers can
        persist the succeeded set and skip those channels on the next retry.

        Args:
            search_report (list): The report to be sent
            report_date (str): The date of the report
            skip_senders (set): Sender class names that already succeeded and
                should be skipped (used on retries to avoid duplicate deliveries)
        """
        skip_senders = skip_senders or set()
        succeeded: set = set()
        failed: dict = {}

        for sender in self.senders:
            sender_name = type(sender).__name__
            if sender_name in skip_senders:
                continue
            try:
                sender.send_report(search_report, report_date)
                succeeded.add(sender_name)
            except Exception as exc:  # noqa: BLE001
                failed[sender_name] = exc

        if failed:
            errors = "; ".join(f"{name}: {err}" for name, err in failed.items())
            raise RuntimeError(f"Notification failed for channel(s): {errors}")

        return succeeded, failed
