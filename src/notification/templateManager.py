from jinja2 import Environment, FileSystemLoader

class TemplateManager:
    def __init__(self, template_dir='templates'):
        self.env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=True,  # Segurança contra XSS
            trim_blocks=True,  # Remove quebras de linha desnecessárias
            lstrip_blocks=True  # Remove espaços em branco à esquerda
        )

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