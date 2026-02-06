"""Module for sending emails."""

import os
import sys
import logging

from tempfile import NamedTemporaryFile

import pandas as pd
import apprise
from airflow.utils.email import send_email

# TODO fix this
# Add parent folder to sys.path in order to be able to import

# Add parent directory to sys.path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


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
                content = self._generate_email_content()

        if skip_notification:
            if self.report_config.skip_null:
                return "skip_notification"
        else:
            content = self._generate_email_content()

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

    def _generate_email_content(self) -> str:
        """Generate HTML content to be sent by email based on
        search_report dictionary
        """

        current_directory = os.path.dirname(__file__)

        tm = TemplateManager(template_dir=os.path.join(current_directory, "templates"))
        report_data = []

        for search in self.search_report:
            headers_list = {}
            header_title = ""
            no_result_message = self.report_config.no_results_found_text

            if search["header"]:
                header_title = search["header"]
                headers_list["header"] = f"{header_title}"

            # Criar filters para este search específico
            filters_content = {}
            if not self.report_config.hide_filters:
                if (
                    search["department"]
                    or search["department_ignore"]
                    or search["pubtype"]
                ):
                    filters_content = {"title": "Filtros Aplicados na Pesquisa:"}

                    if search["department"] and search["department"] is not None:
                        filters_content["included_units"] = {
                            "title": "Unidades Incluídas:",
                            "items": [f"{dpt}" for dpt in search["department"]],
                        }

                    if (
                        search["department_ignore"]
                        and search["department_ignore"] is not None
                    ):
                        filters_content["excluded_units"] = {
                            "title": "Unidades Ignoradas:",
                            "items": [f"{dpt}" for dpt in search["department_ignore"]],
                        }

                    if search["pubtype"] and search["pubtype"] is not None:
                        filters_content["publication_types"] = {
                            "title": "Tipos de Publicações:",
                            "items": [f"{pub}" for pub in search["pubtype"]],
                        }

            for group, search_results in search["result"].items():
                if not search_results:
                    term_data = {
                        "search_terms": {
                            "department": "",
                            "terms": [],
                            "items": [{"header_title": header_title}],
                        },
                        "filters": filters_content,
                        "header_title": header_title,
                    }
                    report_data.append(term_data)
                    continue
                # Group by term - each term will have its own block.
                for term, term_results in search_results.items():
                    # Process each department within this term - create separate block per department
                    for department, results in term_results.items():
                        # Create a separate term_data for each department
                        term_data = {
                            "search_terms": {
                                "department": "",
                                "terms": [],
                                "items": [],
                            },
                            "filters": filters_content,
                            "header_title": header_title,
                        }

                        # Add group information if it's not the default.
                        if not self.report_config.hide_filters:
                            if group != "single_group":
                                term_data["search_terms"]["group"] = group

                        # Add the specific term
                        if not self.report_config.hide_filters:
                            if term != "all_publications":
                                term_data["search_terms"]["terms"].append(f"{term}")
                            else:
                                term_data["search_terms"]["terms"].append(f"{term}")

                        # Add department to terms list if not default
                        if department != "single_department":
                            term_data["search_terms"]["department"] = f"{department}"

                        # Add all results for this term and department.
                        for result in results:
                            title = result["title"] or "Documento sem título"

                            term_data["search_terms"]["items"].append(
                                {
                                    "section": result["section"],
                                    "header_title": header_title,
                                    "title": title,
                                    "url": result["href"],
                                    "url_new_tab": True,
                                    "abstract": result["abstract"],
                                    "date": result["date"],
                                }
                            )

                        report_data.append(term_data)

        return tm.renderizar(
            "dou_template.html",
            results=report_data,
            hide_filters=self.report_config.hide_filters,
            header_text=self.report_config.header_text or None,
            footer=self.report_config.footer_text or None,
            no_results_message=no_result_message,
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