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
class TemplateManager:
    def __init__(self, template_dir='templates'):
        self.env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=True,  # Segurança contra XSS
            trim_blocks=True,  # Remove quebras de linha desnecessárias
            lstrip_blocks=True  # Remove espaços em branco à esquerda
        )
        self.env.filters["markdown"] = markdown_to_html
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