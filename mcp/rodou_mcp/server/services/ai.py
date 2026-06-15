"""AI provider access owned by the MCP server."""

from __future__ import annotations

from ..models import Publication, PublicationContext
from ..settings import Settings

SYSTEM_PROMPT = (
    "Voce e um assistente especializado em publicacoes do Diario Oficial da Uniao. "
    "Responda em portugues brasileiro usando Markdown. Use apenas o contexto "
    "fornecido. Sempre que citar uma publicacao, use um link Markdown no titulo "
    "quando houver URL. Se o contexto nao for suficiente, diga isso."
)


class AIService:
    """Provider-confined answer generation for chatbot requests."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def answer(self, context: PublicationContext) -> str:
        """Generate an answer from database-loaded context."""
        if context.source != "postgres":
            raise ValueError("AI context must be loaded from PostgreSQL")
        question = context.question
        publications = context.publications
        if not publications:
            return "Nao encontrei publicacoes do DOU relacionadas a essa pergunta."
        if not self._settings.ai_provider:
            return self._fallback_answer(publications)
        if not self._settings.ai_api_key:
            raise RuntimeError("RO_DOU_AI_API_KEY must be set when AI provider is enabled")

        prompt = self._build_prompt(context=context)
        try:
            provider = self._settings.ai_provider
            if provider == "openai":
                return self._run_openai(prompt)
            if provider == "gemini":
                return self._run_gemini(prompt)
            if provider == "claude":
                return self._run_claude(prompt)
            if provider == "azure":
                return self._run_azure(prompt)
            raise ValueError(f"Unsupported AI provider: {provider}")
        except Exception as exc:
            return self._provider_error_answer(exc, publications)

    def _build_prompt(self, context: PublicationContext) -> str:
        context_text = "\n\n".join(
            (
                f"ID: {publication.id}\n"
                f"IDMateria: {publication.id_materia or 'N/A'}\n"
                f"Data: {publication.pubdate or 'N/A'}\n"
                f"Secao: {publication.pubname or 'N/A'}\n"
                f"Titulo: {self._markdown_title(publication)}\n"
                f"Categoria: {publication.category or 'N/A'}\n"
                f"Tipo: {publication.article_type or 'N/A'}\n"
                f"Texto: {(publication.body or '')[: self._settings.ai_context_body_chars]}"
            )
            for publication in context.publications
        )
        return (
            f"Pergunta: {context.question}\n\n"
            f"Fonte do contexto: {context.source}\n"
            f"Data do contexto: {context.context_date or 'N/A'}\n"
            f"Total de publicacoes carregadas do banco: {context.total_publications}\n\n"
            "Contexto: publicacoes do Diario Oficial carregadas previamente do banco PostgreSQL.\n"
            "Responda em Markdown, com listas quando ajudar a leitura, e inclua "
            "links das materias citadas.\n\n"
            f"{context_text}"
        )

    @staticmethod
    def _fallback_answer(publications: list[Publication]) -> str:
        lines = [
            "Encontrei publicacoes do dia. Configure um provedor de IA no MCP server para uma resposta sintetizada:"
        ]
        for publication in publications[:5]:
            title = publication.title or "Sem titulo"
            date = publication.pubdate or "sem data"
            label = f"{title} ({publication.id})"
            if publication.url:
                label = f"[{label}]({publication.url})"
            lines.append(f"- {label} - {date}")
        return "\n".join(lines)

    def _provider_error_answer(
        self,
        error: Exception,
        publications: list[Publication],
    ) -> str:
        provider = self._settings.ai_provider or "IA"
        lines = [
            f"O provedor `{provider}` recusou a chamada ou atingiu limite de uso.",
            "",
            f"Detalhe técnico: `{type(error).__name__}`.",
            "",
            "Enquanto isso, estas são algumas publicações do dia disponíveis para consulta:",
        ]
        for publication in publications[:10]:
            title = publication.title or "Sem titulo"
            label = f"{title} ({publication.id})"
            if publication.url:
                label = f"[{label}]({publication.url})"
            lines.append(f"- {label}")
        return "\n".join(lines)

    @staticmethod
    def _markdown_title(publication: Publication) -> str:
        title = publication.title or "Sem titulo"
        if publication.url:
            return f"[{title}]({publication.url})"
        return title

    def _run_openai(self, prompt: str) -> str:
        from openai import OpenAI

        client = OpenAI(api_key=self._settings.ai_api_key)
        response = client.chat.completions.create(
            model=self._settings.ai_model or "gpt-4.1-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=self._settings.ai_temperature,
            max_tokens=self._settings.ai_max_tokens,
        )
        return response.choices[0].message.content or ""

    def _run_gemini(self, prompt: str) -> str:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=self._settings.ai_api_key)
        response = client.models.generate_content(
            model=self._settings.ai_model or "gemini-2.0-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=self._settings.ai_temperature,
                max_output_tokens=self._settings.ai_max_tokens,
            ),
        )
        return response.text or ""

    def _run_claude(self, prompt: str) -> str:
        from anthropic import Anthropic

        client = Anthropic(api_key=self._settings.ai_api_key)
        response = client.messages.create(
            model=self._settings.ai_model or "claude-3-5-haiku-latest",
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
            temperature=self._settings.ai_temperature,
            max_tokens=self._settings.ai_max_tokens,
        )
        return response.content[0].text

    def _run_azure(self, prompt: str) -> str:
        from openai import AzureOpenAI

        if not self._settings.azure_openai_endpoint:
            raise RuntimeError("AZURE_OPENAI_ENDPOINT must be set for Azure")
        if not self._settings.azure_openai_api_version:
            raise RuntimeError("AZURE_OPENAI_API_VERSION must be set for Azure")
        if not self._settings.ai_model:
            raise RuntimeError("RO_DOU_AI_MODEL must be set to the Azure deployment name")

        client = AzureOpenAI(
            api_key=self._settings.ai_api_key,
            azure_endpoint=self._settings.azure_openai_endpoint,
            api_version=self._settings.azure_openai_api_version,
        )
        response = client.chat.completions.create(
            model=self._settings.ai_model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=self._settings.ai_temperature,
            max_tokens=self._settings.ai_max_tokens,
        )
        return response.choices[0].message.content or ""
