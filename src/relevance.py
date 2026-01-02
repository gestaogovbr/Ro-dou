"""
Módulo responsável por decidir a relevância semântica de entradas do DOU.
Ponto único de evolução para heurísticas, ML ou LLM.
"""

KEYWORDS = [
    "nomeia",
    "nomear",
    "exonera",
    "exonerar",
    "designa",
    "dispensa",
    "revoga",
    "autoriza",
    "homologa",
    "torna sem efeito",
]


def is_relevant_entry(entry: dict) -> bool:
    """
    Decide se um item retornado do DOU é relevante.

    Regra atual:
    - Heurística conservadora
    - Alto recall
    - Nenhuma dependência externa
    """

    if not entry:
        return False

    text = (
        entry.get("texto")
        or entry.get("content")
        or entry.get("body")
        or ""
    )

    text = text.lower()

    if any(keyword in text for keyword in KEYWORDS):
        return True

    # fallback conservador
    return True
