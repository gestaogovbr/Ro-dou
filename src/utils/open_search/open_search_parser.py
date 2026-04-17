"""Module to parse Open Search XML responses from the Diário Oficial da União (DOU)."""

from lxml import etree  # type: ignore
import re
from datetime import datetime


class DOUXmlParser:
    """Parser for Open Search XML responses from the DOU."""

    def _extract_plain_text(self, html_content: str) -> str:
        """Remove HTML tags from a string and normalize whitespace.

        Args:
            html_content (str): String containing HTML.

        Returns:
            str: Plain text with HTML tags removed and whitespace normalized.
        """
        cleaned = re.sub("<[^>]+>", " ", html_content)
        cleaned = re.sub("\s+", " ", cleaned)
        return cleaned.strip()

    def _get_assina(self, html_content: str) -> str | None:
        """Extract the signature text from a DOU article HTML content.

        Searches for all `<p class="assina">` tags and joins their text
        content with ", ".

        Args:
            html_content (str): String containing the article HTML.

        Returns:
            str | None: Comma-separated signatures if found, None otherwise.
        """
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html_content, "html.parser")
        p_tags = soup.find_all("p", class_="assina")
        return ", ".join([p.text for p in p_tags]) if p_tags else None

    def parse_dou_xml(self, xml_str: str) -> dict:
        """Parse an Open Search XML response from the DOU and return a structured dictionary.

        Args:
            xml_str (str): String containing the XML returned by the Open Search API.

        Returns:
            dict: Dictionary with article metadata and body, containing the keys:
                - article_id (str): Article identifier.
                - name (str): Article name.
                - id_oficio (str): Official document identifier.
                - pub_name (str): Publication name.
                - art_type (str): Article type.
                - pub_date (str): Publication date.
                - art_class (str): Article class.
                - art_category (str): Article category.
                - art_size (int): Article size in characters.
                - number_page (int): Page number.
                - pdf_page (str): Page in the PDF.
                - edition_number (int): Edition number.
                - id_materia (str): Subject identifier.
                - body (dict): Article body with the keys:
                    - identifica (str): Identifying header.
                    - data (str): Date present in the article body.
                    - texto_html (str): Article text in HTML.
                    - texto_plain (str): Article text without HTML tags.
                    - assina: (str): Signature text from a DOU article HTML content.
                    - ementa: (str): Ementa text from a DOU article HTML content.
        """
        root = etree.fromstring(xml_str.encode("utf-8"))
        article = root.find(".//article")

        def get_attr(name):
            return article.get(name)

        body = article.find("body")
        texto_element = body.find("Texto")
        if texto_element is not None:
            texto_html = (texto_element.text or "") + "".join(
                etree.tostring(child, encoding="unicode") for child in texto_element
            )
        else:
            texto_html = ""

        doc = {
            "id": get_attr("id"),
            "name": get_attr("name"),
            "id_oficio": get_attr("idOficio"),
            "pubname": get_attr("pubName"),
            "arttype": get_attr("artType"),
            "pubdate": datetime.strptime(get_attr("pubDate"), "%d/%m/%Y").strftime(
                "%Y-%m-%d"
            ),
            "art_class": get_attr("artClass"),
            "artcategory": get_attr("artCategory"),
            "art_size": int(get_attr("artSize")),
            "number_page": int(get_attr("numberPage")),
            "pdfpage": get_attr("pdfPage"),
            "edition_number": get_attr("editionNumber"),
            "id_materia": get_attr("idMateria"),
            "identifica": body.findtext("Identifica"),
            "data": body.findtext("Data"),
            "texto": texto_html,
            "texto_plain": self._extract_plain_text(texto_html),
            "assina": self._get_assina(texto_html),
            "ementa": body.findtext("Ementa"),
        }

        return doc
