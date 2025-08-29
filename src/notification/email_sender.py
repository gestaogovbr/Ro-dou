"""Module for sending emails."""

from __future__ import annotations

import os
import sys
import textwrap
from tempfile import NamedTemporaryFile

import markdown
import pandas as pd
from airflow.utils.email import send_email

# --- import helpers (mantendo compat com estrutura atual do repo) ---
# adiciona o diretório pai ao sys.path pra permitir `from notification.isender import ISender`
_PARENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PARENT_DIR not in sys.path:
    sys.path.insert(0, _PARENT_DIR)

from notification.isender import ISender  # noqa: E402
from schemas import ReportConfig  # noqa: E402


class EmailSender(ISender):
    """Prepare and send e-mails with the reports."""

    # mantido (caso algum highlight seja aplicado em outro ponto do pipeline)
    highlight_tags = ("<span class='highlight' style='background:#FFA;'>", "</span>")

    def __init__(self, report_config: ReportConfig) -> None:
        self.report_config = report_config
        self.search_report: list = []
        # mantém o watermark do upstream (com a marca institucional)
        self.watermark = """
            <div class="footer" style="margin-top:24px;">
                <a href="https://www.gov.br/gestao/pt-br/assuntos/gestaoeinovacao/ro-dou">
                    <img src="https://www.gov.br/gestao/pt-br/assuntos/gestaoeinovacao/ro-dou/ro-dou/@@govbr.institucional.banner/b27393f0-d00b-4459-8c99-f4f084eb2432/@@images/ecce877d-c42d-4ab6-ad9b-d24073ab5063.png"
                         alt="Ro-DOU" width="250">
                </a>
                <small>Esta pesquisa foi realizada automaticamente pelo
                    <a href="https://gestaogovbr.github.io/Ro-dou/">&copy; Ro-DOU</a>
                </small>
            </div>
        """

    # -----------------------------
    # envio principal
    # -----------------------------
    def send(self, search_report: list, report_date: str):
        """Build the email content (+ optional CSV) and send it."""
        self.search_report = search_report
        full_subject = f"{self.report_config.subject} - DOs de {report_date}"

        # determina se deve enviar (skip quando não há nenhum resultado)
        skip_notification = True
        for search in self.search_report:
            # se em qualquer grupo houver itens, envia
            has_any = any(bool(v) for v in search.get("result", {}).values())
            if has_any:
                skip_notification = False
                break

        if skip_notification and self.report_config.skip_null:
            return "skip_notification"

        # conteúdo de e-mail
        content = (
            self.report_config.no_results_found_text
            if skip_notification
            else self.generate_email_content()
        )
        content += self.watermark

        # anexo CSV se solicitado e houver resultados
        if self.report_config.attach_csv and not skip_notification:
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

    # -----------------------------
    # geração do HTML
    # -----------------------------
    def generate_email_content(self) -> str:
        """Generate HTML content to be sent by email based on search_report dictionary."""
        current_directory = os.path.dirname(__file__)
        parent_directory = os.path.dirname(current_directory)

        # CSS do e-mail
        file_path = os.path.join(parent_directory, "report_style.css")
        blocks: list[str] = []
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                blocks.append(f"<style>\n{f.read()}</style>")
        except FileNotFoundError:
            # segue sem CSS se o arquivo não existir
            pass

        if self.report_config.header_text:
            blocks.append(self.report_config.header_text)

        already_included_ids: set[str] = set()

        for search in self.search_report:
            # cabeçalho da consulta
            header = search.get("header")
            if header:
                blocks.append(f"<h2>{header}</h2>")

            # filtros aplicados
            if not self.report_config.hide_filters:
                dept = search.get("department") or []
                dept_ign = search.get("department_ignore") or []
                pubtype = search.get("pubtype") or []
                if dept or dept_ign or pubtype:
                    blocks.append("<p class='secao-marker'>Filtrando resultados somente para:</p>")
                    if dept:
                        blocks.append(f"<p><strong>Unidades:</strong> {', '.join(dept)}</p>")
                    if dept_ign:
                        blocks.append(f"<p><strong>Ignorar:</strong> {', '.join(dept_ign)}</p>")
                    if pubtype:
                        blocks.append(f"<p><strong>Tipos de publicação:</strong> {', '.join(pubtype)}</p>")

            # resultados por grupo/termo/unidade
            result_by_group = search.get("result", {})
            if not result_by_group:
                blocks.append(f"<p>{self.report_config.no_results_found_text}.</p>")
                continue

            for group, search_results in result_by_group.items():
                if not search_results:
                    blocks.append(f"<p>{self.report_config.no_results_found_text}.</p>")
                    continue

                if not self.report_config.hide_filters and group != "single_group":
                    blocks.append(f"<p><strong>Grupo:</strong> {group}</p>")

                for term, term_results in search_results.items():
                    if not self.report_config.hide_filters:
                        if term != "all_publications":
                            blocks.append(f"<p><em># Resultados para: {term}</em></p>")
                        else:
                            blocks.append("<p><strong>Publicações:</strong></p>")

                    for department, results in term_results.items():
                        if not self.report_config.hide_filters and department != "single_department":
                            blocks.append(f"<p><strong>{department}</strong></p>")

                        for result in results:
                            # dedupe por id quando disponível
                            result_id = result.get("id")
                            if result_id:
                                if result_id in already_included_ids:
                                    continue
                                already_included_ids.add(result_id)

                            sec_desc = result.get("section") or ""
                            title = result.get("title") or "Documento sem título"
                            href = result.get("href") or "#"
                            abstract = result.get("abstract") or ""
                            date = result.get("date") or ""

                            item_html = f"""
                                <p class="secao-marker">{sec_desc}</p>
                                <h3><a href="{href}">{title}</a></h3>
                                <p style='text-align:justify' class='abstract-marker'>{abstract}</p>
                                <p class='date-marker'>{date}</p>
                            """
                            blocks.append(textwrap.dedent(item_html))

        blocks.append("<hr />")
        if self.report_config.footer_text:
            blocks.append(self.report_config.footer_text)

        # usamos markdown pra permitir elementos Markdown e deixar HTML passar
        return markdown.markdown("\n".join(blocks))

    # -----------------------------
    # CSV helpers
    # -----------------------------
    def get_csv_tempfile(self) -> NamedTemporaryFile:
        """Gera um tempfile com o CSV; o caller deve fechar/deletar após o envio."""
        # NamedTemporaryFile em modo texto e não excluir ao fechar (Airflow anexa pelo caminho)
        tmp = NamedTemporaryFile(prefix="extracao_dou_", suffix=".csv", mode="w+", delete=False, encoding="utf-8")
        df = self.convert_report_to_dataframe()
        df.to_csv(tmp, index=False)
        tmp.flush()
        tmp.seek(0)
        return tmp

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
            if search.get("header") is not None:
                del_header = False

            for group, search_result in (search.get("result") or {}).items():
                if group != "single_group":
                    del_single_group = False
                for _, term_results in (search_result or {}).items():
                    for dpt, _ in (term_results or {}).items():
                        if dpt != "single_department":
                            del_single_department = False

        # remove colunas quando são só “valores padrão”
        if del_header and "Consulta" in df.columns:
            del df["Consulta"]

        if del_single_group and "Grupo" in df.columns:
            del df["Grupo"]
        else:
            if "Grupo" in df.columns:
                df["Grupo"] = df["Grupo"].replace("single_group", "")

        if del_single_department and "Unidade" in df.columns:
            del df["Unidade"]
        else:
            if "Unidade" in df.columns:
                df["Unidade"] = df["Unidade"].replace("single_department", "")

        return df

    def convert_report_dict_to_tuple_list(self) -> list[tuple]:
        tuple_list: list[tuple] = []
        for search in self.search_report:
            header = search.get("header") if search.get("header") else None
            for group, results in (search.get("result") or {}).items():
                for term, departments in (results or {}).items():
                    for department, dpt_matches in (departments or {}).items():
                        for match in (dpt_matches or []):
                            tuple_list.append(
                                repack_match(header, group, term, department, match)
                            )
        return tuple_list


def repack_match(
    header: str | None, group: str, search_term: str, department: str, match: dict
) -> tuple:
    return (
        header,
        group,
        search_term,
        department,
        match.get("section"),
        match.get("href"),
        match.get("title"),
        match.get("abstract"),
        match.get("date"),
    )
