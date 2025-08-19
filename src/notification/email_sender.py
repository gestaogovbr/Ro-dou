"""Module for sending emails."""

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
from notification.templateManager import TemplateManager

from schemas import ReportConfig


class EmailSender(ISender):
    """Prepare and send e-mails with the reports."""

    highlight_tags = ("<span class='highlight' style='background:#FFA;'>", "</span>")

    def __init__(self, report_config: ReportConfig) -> None:
        self.report_config = report_config
        self.search_report = ""
        self.watermark = ""

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
                content = self.generate_email_content()

        if skip_notification:
            if self.report_config.skip_null:
                return "skip_notification"
        else:
            content = self.generate_email_content()

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

        # Inicializar o gerenciador de templates
        tm = TemplateManager(template_dir=os.path.join(current_directory, "templates"))

        for search in self.search_report:
            header_title = ""

            if search["header"]:
                header_title = search["header"]

            filters = {}

            if not self.report_config.hide_filters:
                if (
                    search["department"]
                    or search["department_ignore"]
                    or search["pubtype"]
                ):
                    filters = {"title": "Filtros Aplicados na Pesquisa:"}
                    if search["department"]:
                        filters["included_units"] = {
                            "title": "Unidades Incluídas:",
                            "items": [f"{dpt}" for dpt in search["department"]],
                        }

                    if search["department_ignore"]:
                        filters["excluded_units"] = {
                            "title": "Unidades Ignoradas:",
                            "items": [f"{dpt}" for dpt in search["department_ignore"]],
                        }

                    if search["pubtype"]:
                        filters["publication_types"] = {
                            "title": "Tipos de Publicações:",
                            "items": [f"{pub}" for pub in search["pubtype"]],
                        }

            filters = {"filters": filters}
            results_data = []

            for group, search_results in search["result"].items():
                term_data = {"search_terms": {"terms": [], "items": []}}

                if not self.report_config.hide_filters:
                    if group != "single_group":
                        term_data["search_terms"]["terms"].append(f"{group}")

                for term, term_results in search_results.items():
                    if not self.report_config.hide_filters:
                        term_data["search_terms"]["terms"].append(f"{term}")

                    for department, results in term_results.items():
                        if (
                            not self.report_config.hide_filters
                            and department != "single_department"
                        ):
                            term_data["search_terms"]["terms"].append(f"{department}")

                        for result in results:
                            if not self.report_config.hide_filters:
                                sec_desc = result["section"]
                                title = result["title"]
                                if not result["title"]:
                                    title = "Documento sem título"

                                term_data["search_terms"]["items"].append(
                                    {
                                        "section": sec_desc,
                                        "title": title,
                                        "url": result["href"],
                                        "url_new_tab": True,
                                        "abstract": result["abstract"],
                                        "date": result["date"],
                                    }
                                )
                            else:
                                title = result["title"]
                                if not result["title"]:
                                    title = "Documento sem título"

                                term_data["search_terms"]["items"].append(
                                    {
                                        "section": sec_desc,
                                        "title": title,
                                        "url": result["href"],
                                        "url_new_tab": True,
                                        "abstract": result["abstract"],
                                        "date": result["date"],
                                    }
                                )
                results_data.append(term_data)

        return tm.renderizar(
            "dou_template.html",
            filters=filters,
            results=results_data,
            header_title=header_title,
            header_text=self.report_config.header_text or None,
            footer_text=self.report_config.footer_text or None,
        )

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
                    for dpt, _ in term_results.items():
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
