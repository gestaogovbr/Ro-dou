from airflow.sdk import Variable

from ai.runner import AIRunner
from schemas import AIConfig, AIReportConfig
from bs4 import BeautifulSoup

def extract_publications(
    search_results: list[dict],
    limit: int | None = None,
) -> list[dict]:
    """Extract pubs and eliminate duplicates."""

    selected = []
    seen = set()

    for search in search_results:
        groups = search.get("result", {})

        for group_results in groups.values():
            for term_results in group_results.values():
                for publications in term_results.values():
                    for publication in publications:
                        abstract = publication.get("abstract")

                        if not abstract or not abstract.strip():
                            continue

                        identity = (
                            publication.get("id")
                            or publication.get("href")
                            or (
                                publication.get("title"),
                                publication.get("date"),
                                abstract,
                            )
                        )

                        if identity in seen:
                            continue

                        seen.add(identity)
                        selected.append(
                            {
                                "title": publication.get("title"),
                                "section": publication.get("section"),
                                "date": publication.get("date"),
                                "href": publication.get("href"),
                                "abstract": abstract.strip(),
                            }
                        )

                        if limit is not None and len(selected) >= limit:
                            return selected

    return selected


def serialize_publications(publications: list[dict]) -> str:
    """Convert publicações in structured text."""

    blocks = []

    for index, publication in enumerate(publications, start=1):
        abstract = publication.get("abstract", "")
        abstract = BeautifulSoup(
            str(abstract),
            "html.parser",
        ).get_text(" ", strip=True)

        if not abstract:
            continue

        lines = [f"PUBLICAÇÃO {index}"]

        if publication.get("title"):
            lines.append(f"Título: {publication['title']}")

        if publication.get("section"):
            lines.append(f"Seção: {publication['section']}")

        if publication.get("date"):
            lines.append(f"Data: {publication['date']}")

        lines.append(f"Resumo: {abstract}")

        blocks.append("\n".join(lines))

    return "\n\n".join(blocks)


def generate_executive_summary(
    search_results: list[dict],
    ai_config: AIConfig,
    report_config: AIReportConfig,
) -> tuple[str, str | None]:
    publications = extract_publications(
        search_results,
        limit=report_config.ai_executive_pub_limit,
    )

    if not publications:
        return "", None

    input_text = serialize_publications(publications)

    return AIRunner.run(
        provider=ai_config.provider,
        api_key=Variable.get(ai_config.api_key_var),
        model=ai_config.model,
        input_text=input_text,
        system_prompt=report_config.ai_executive_custom_prompt,
        max_tokens=report_config.executive_max_tokens,
        temperature=report_config.executive_temperature,
    )
