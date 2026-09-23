from urllib.parse import urlsplit

import nh3
import markdown

from jinja2 import Environment, FileSystemLoader
from markupsafe import Markup


_ALLOWED_MARKDOWN_TAGS = {
    "p",
    "br",
    "strong",
    "em",
    "ul",
    "ol",
    "li",
    "blockquote",
    "code",
    "pre",
    "h1",
    "h2",
    "h3",
    "h4",
}

def markdown_to_html(value: str | None) -> Markup:
    if not value:
        return Markup("")

    converted = markdown.markdown(
        value,
        extensions=["sane_lists", "nl2br"],
    )

    # sanitize to avoid raw html
    sanitized = nh3.clean(
        converted,
        tags=_ALLOWED_MARKDOWN_TAGS,
        attributes={},
        clean_content_tags={"script", "style"},
        url_schemes=set(),
    )

    return Markup(sanitized)


# Tags permitidas no conteúdo vindo das fontes externas (DOU, INLABS,
# Querido Diário, DOESP). Sem <a> e <img> para impedir links forjados e
# pixels de rastreamento no e-mail institucional.
_ALLOWED_CONTENT_TAGS = {"p", "br", "strong", "em", "b", "i", "span"}

_ALLOWED_URL_SCHEMES = {"http", "https"}


def _keep_only_highlight_class(tag: str, attr: str, value: str) -> str | None:
    """Mantém apenas ``class="highlight"`` em ``<span>`` (destaque do termo)."""
    if tag == "span" and attr == "class" and value == "highlight":
        return value
    return None


def sanitize_html(value: str | None) -> Markup:
    """Sanitiza HTML de origem externa antes de renderizá-lo no template."""
    if not value:
        return Markup("")

    sanitized = nh3.clean(
        str(value),
        tags=_ALLOWED_CONTENT_TAGS,
        attributes={"span": {"class"}},
        attribute_filter=_keep_only_highlight_class,
        clean_content_tags={"script", "style"},
        url_schemes=set(),
    )

    return Markup(sanitized)


def safe_url(value: str | None) -> str:
    """Retorna a URL se ela for http(s) com host; caso contrário, string vazia."""
    if not value:
        return ""

    url = str(value).strip()
    try:
        parts = urlsplit(url)
    except ValueError:
        return ""

    if parts.scheme.lower() not in _ALLOWED_URL_SCHEMES or not parts.hostname:
        return ""

    return url


class TemplateManager:
    def __init__(self, template_dir='templates'):
        self.env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=True,  # Segurança contra XSS
            trim_blocks=True,  # Remove quebras de linha desnecessárias
            lstrip_blocks=True  # Remove espaços em branco à esquerda
        )
        self.env.filters["markdown"] = markdown_to_html
        self.env.filters["sanitize_html"] = sanitize_html
        self.env.filters["safe_url"] = safe_url

    def renderizar(self, template_name, filters=None, results=None, **context):
        """
        Renders DOU results using a Jinja2 template.

        Args:
            template_name: Template file name
            filters: Dict with filters applied
            results: List of search results
            header_title: Header title (optional)

        Returns:
            str: HTML rendered
        """
        try:
            template = self.env.get_template(template_name)
            return template.render(
                filters=filters,
                results=results,
                **context
            )
        except Exception as e:
            print(f"Erro na renderização: {e}")
            import traceback
            traceback.print_exc()
            return None