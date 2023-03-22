import ast
import os
import sys
import textwrap
from tempfile import NamedTemporaryFile

import markdown
import pandas as pd
from airflow.utils.email import send_email

# TODO fix this
# Add parent folder to sys.path in order to be able to import
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from notification.discord_sender import DiscordSender
from parsers import DAGConfig
from util import get_source_dir


class Notifier:
    """Performs the notification delivery through different means as
    defined in the YAML file. Currently it sends notification to email
    and Discord.
    """

    def __init__(self, specs: DAGConfig) -> None:
        self.specs = specs


    def send_notification(self, search_report: str, report_date: str):
        self.report_date = report_date
        # Convert to data structure after it's retrieved from xcom
        self.search_report = ast.literal_eval(search_report)
        if self.specs.discord_webhook:
            DiscordSender(self.specs.discord_webhook).send_discord(search_report)
        else:
            self._send_email()


    def _send_email(self):
        """Builds the email content, the CSV if applies, and send it
        """
        full_subject = f"{self.specs.subject} - DOs de {self.report_date}"
        items = ['contains' for k, v in self.search_report.items() if v]
        if items:
            content = self.generate_email_content()
        else:
            if self.specs.skip_null:
                return 'skip_notification'
            content = "Nenhum dos termos pesquisados foi encontrado."

        if self.specs.attach_csv and items:
            with self.get_csv_tempfile() as csv_file:
                send_email(
                    to=self.specs.emails,
                    subject=full_subject,
                    files=[csv_file.name],
                    html_content=content,
                    mime_charset='utf-8')
        else:
            send_email(
                to=self.specs.emails,
                subject=full_subject,
                html_content=content,
                mime_charset='utf-8')


    def generate_email_content(self) -> str:
        """Generate HTML content to be sent by email based on
        search_report dictionary
        """
        with open(os.path.join(get_source_dir(), 'report_style.css'), 'r') as f:
            blocks = [f'<style>\n{f.read()}</style>']

        for group, results in self.search_report.items():
            if group != 'single_group':
                blocks.append('\n')
                blocks.append(f'**Grupo: {group}**')
                blocks.append('\n\n')

            for term, items in results.items():
                blocks.append('\n')
                blocks.append(f'* # Resultados para: {term}')

                for item in items:
                    sec_desc = item['section']
                    item_html = f"""
                        <p class="secao-marker">{sec_desc}</p>
                        ### [{item['title']}]({item['href']})
                        <p class='abstract-marker'>{item['abstract']}</p>
                        <p class='date-marker'>{item['date']}</p>"""
                    blocks.append(
                        textwrap.indent(textwrap.dedent(item_html), ' ' * 4))
                blocks.append('---')
            blocks.append('---')

        return markdown.markdown('\n'.join(blocks))


    def get_csv_tempfile(self) -> NamedTemporaryFile:
        temp_file = NamedTemporaryFile(prefix='extracao_dou_', suffix='.csv')
        self.convert_report_to_dataframe().to_csv(temp_file, index=False)
        return temp_file


    def convert_report_to_dataframe(self) -> pd.DataFrame:
        df = pd.DataFrame(self.convert_report_dict_to_tuple_list())
        df.columns = ['Grupo', 'Termo de pesquisa', 'Seção', 'URL',
                        'Título', 'Resumo', 'Data']
        if 'single_group' in self.search_report:
            del df['Grupo']
        return df


    def convert_report_dict_to_tuple_list(self) -> list:
        tuple_list = []
        for group, results in self.search_report.items():
            for term, matches in results.items():
                for match in matches:
                    tuple_list.append(repack_match(group, term, match))
        return tuple_list




def repack_match(group: str, search_term: str, match: dict) -> tuple:
    return (group,
            search_term,
            match['section'],
            match['href'],
            match['title'],
            match['abstract'],
            match['date'])
