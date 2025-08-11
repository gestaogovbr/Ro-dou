"""Module for sending emails.
"""

import os
import sys
from tempfile import NamedTemporaryFile
import textwrap

import markdown
import pandas as pd
from airflow.utils.email import send_email

# TODO fix this
# Add parent folder to sys.path in order to be able to import

# Add parent directory to sys.path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# current_dir = os.path.dirname(os.path.abspath(__file__))
# parent_dir = os.path.dirname(current_dir)

sys.path.insert(0, parent_dir)

from notification.isender import ISender
from schemas import ReportConfig


class EmailSender(ISender):
    """Prepare and send e-mails with the reports."""

    highlight_tags = ("<span class='highlight' style='background:#FFA;'>", "</span>")

    def __init__(self, report_config: ReportConfig) -> None:
        self.report_config = report_config
        self.search_report = ""
        self.watermark = """
            <div class="footer">
                <a href="https://www.gov.br/gestao/pt-br/assuntos/gestaoeinovacao/ro-dou">
                    <img src="https://www.gov.br/gestao/pt-br/assuntos/gestaoeinovacao/ro-dou/ro-dou/@@govbr.institucional.banner/b27393f0-d00b-4459-8c99-f4f084eb2432/@@images/ecce877d-c42d-4ab6-ad9b-d24073ab5063.png"
                    alt="Ro-DOU" width="250">
                </a>
                <small>Esta pesquisa foi realizada automaticamente pelo
                    <a href="https://gestaogovbr.github.io/Ro-dou/">&copy; Ro-DOU</a>
                </small>
            </div>
        """

    def send(self, search_report: list, report_date: str):
        """Builds the email content, the CSV if applies, and send it"""
        self.search_report = search_report
        full_subject = f"{self.report_config.subject} - DOs de {report_date}"
        skip_notification = True
        for search in self.search_report:
            items = ["contains" for k, v in search["result"].items() if v]
            if items:
                skip_notification = False
            else:
                content = self.report_config.no_results_found_text

        if skip_notification:
            if self.report_config.skip_null:
                return "skip_notification"
        else:
            content = self.generate_email_content()

        content += self.watermark

        if self.report_config.attach_csv and skip_notification is False:
            with self.get_csv_tempfile() as csv_file:
                send_email(
                    to=self.report_config.emails,
                    subject=full_subject,
                    files=[csv_file.name],
                    html_content=content,
                    mime_charset="utf-8",
                )
        else:
            send_email(
                to=self.report_config.emails,
                subject=full_subject,
                html_content=content,
                mime_charset="utf-8",
            )

    def generate_email_content(self) -> str:
        """Generate HTML content to be sent by email based on
        search_report dictionary
        """

        current_directory = os.path.dirname(__file__)
        parent_directory = os.path.dirname(current_directory)

        # File with email styling
        file_path = os.path.join(parent_directory, "report_style.css")

        with open(file_path, "r", encoding="utf-8") as f:
            blocks = [f"<style>\n{f.read()}</style>"]

        if self.report_config.header_text:
            blocks.append(self.report_config.header_text)

        for search in self.search_report:

            if search["header"]:
                blocks.append(f"<h2>{search['header']}</h2>")

            if not self.report_config.hide_filters:
                if search["department"] or search["department_ignore"] or search["pubtype"]:
                    blocks.append(
                        """<p class="secao-marker">Filtrando resultados somente para:</p>"""
                    )
                    if search["department"]:
                        blocks.append("<small>Unidades:</small>")
                        blocks.append("<ul>")
                        for dpt in search["department"]:
                            blocks.append(f"<li><small>{dpt}</small></li>")
                        blocks.append("</ul>")

                    if search["department_ignore"]:
                        blocks.append("<small>Desconsiderar Unidades (e subordinadas):</small>")
                        blocks.append("<ul>")
                        for dpt in search["department_ignore"]:
                            blocks.append(f"<li><small>{dpt}</small></li>")
                        blocks.append("</ul>")


                    if search["pubtype"]:
                        blocks.append("<small>Tipos de publicações:</small>")
                        blocks.append("<ul>")
                        for pub in search["pubtype"]:
                            blocks.append(f"<li><small>{pub}</small></li>")
                        blocks.append("</ul>")

            for group, search_results in search["result"].items():

                if not search_results:
                    blocks.append(f"<p>{self.report_config.no_results_found_text}.</p>")
                else:
                    if not self.report_config.hide_filters:
                        if group != "single_group":
                            blocks.append("\n")
                            blocks.append(f"**Grupo: {group}**")
                            blocks.append("\n\n")

                    for term, term_results in search_results.items():
                        blocks.append("\n")
                        if not self.report_config.hide_filters:
                            blocks.append(f"* # Resultados para: {term}")

                        for department, results in term_results.items():

                            if (
                                not self.report_config.hide_filters
                                and department != "single_department"
                            ):                            
                                blocks.append(f"**{department}**") 

                            for result in results:
                                if not self.report_config.hide_filters:
                                    sec_desc = result["section"]
                                    title = result["title"]
                                    if not result["title"]:
                                        title = "Documento sem título"
                                    item_html = f"""
                                        <p class="secao-marker">{sec_desc}</p>                                         
                                         ### [{title}]({result['href']})
                                        <p style='text-align:justify' class='abstract-marker'>{result['abstract']}</p>
                                        <p class='date-marker'>{result['date']}</p>"""
                                    blocks.append(
                                        textwrap.indent(
                                            textwrap.dedent(item_html), " " * 4
                                        )
                                    )
                                else:
                                    item_html = f"""
                                        ### [{result['title']}]({result['href']})
                                        <p style='text-align:justify' class='abstract-marker'>{result['abstract']}</p><br><br>"""
                                    blocks.append(textwrap.dedent(item_html))

        blocks.append("---")
        if self.report_config.footer_text:
            blocks.append(self.report_config.footer_text)

        return markdown.markdown("\n".join(blocks))

    def get_csv_tempfile(self) -> NamedTemporaryFile:
        temp_file = NamedTemporaryFile(prefix="extracao_dou_", suffix=".csv")
        self.convert_report_to_dataframe().to_csv(temp_file, index=False)
        return temp_file

    def convert_report_to_dataframe(self) -> pd.DataFrame:
        df = pd.DataFrame(self.convert_report_dict_to_tuple_list())
        df.columns = [
            "Consulta",
            "Grupo",
            "Termo de pesquisa",
            "Unidade",
            "Seção",
            "URL",
            "Título",
            "Resumo",
            "Data",
        ]
        del_header = True
        del_single_group = True
        del_single_department = True

        for search in self.search_report:
            if search["header"] is not None:
                del_header = False

            for group, search_result in search["result"].items():
                if group != "single_group":
                    del_single_group = False
                for _, term_results in search_result.items():
                    for dpt,_ in term_results.items():
                        if dpt != "single_department":
                            del_single_department = False

        # Drop empty or default columns
        if del_header:
            del df["Consulta"]

        if del_single_group:
            del df["Grupo"]
        else:
            # Replace single_group with blank
            df["Grupo"] = df["Grupo"].replace("single_group", "")

        if del_single_department:
            del df["Unidade"]
        else:
            # Replace single_group with blank
            df["Unidade"] = df["Unidade"].replace("single_department", "")

        return df

    def convert_report_dict_to_tuple_list(self) -> list:
        tuple_list = []
        for search in self.search_report:
            header = search["header"] if search["header"] else None
            for group, results in search["result"].items():
                for term, departments in results.items():
                    for department, dpt_matches in departments.items():
                        for match in dpt_matches:
                            tuple_list.append(
                                repack_match(header, group, term, department, match)
                            )
        return tuple_list


def repack_match(
    header: str, group: str, search_term: str, department: str, match: dict
) -> tuple:
    return (
        header,
        group,
        search_term,
        department,
        match["section"],
        match["href"],
        match["title"],
        match["abstract"],
        match["date"],
    )
