import copy

import pytest
import pandas as pd
import numpy as np
from datetime import datetime
import importlib.util
from datetime import datetime
from unittest.mock import MagicMock, patch
from airflow.models import Variable
from ai.provider import AIProvider
from schemas import AIConfig, AISearchConfig, NeuralSearchConfig

# Same layout as Airflow image / conftest (mounted `src` as `dags.ro_dou_src`).
_INLABS_HOOK = (
    "dags.ro_dou_src.hooks.inlabs_hook"
    if importlib.util.find_spec("dags.ro_dou_src.hooks.inlabs_hook")
    else "hooks.inlabs_hook"
)

Variable.set("KEY", "fake-key-for-tests")

_MIN_AI_CONFIG = AIConfig(
    provider=AIProvider.openai,
    api_key_var="KEY",
    model="gpt-4o-mini",
)

_MIN_AI_SEARCH_CONFIG = AISearchConfig(use_ai_summary=False, has_ementa=False)


@pytest.mark.parametrize(
    "text_terms_in, text_terms_out",
    [
        (["lorem & ( ipsum | dolor)"], ["lorem", "ipsum", "dolor"]),
    ],
)
def test_filter_text_terms(inlabs_hook, text_terms_in, text_terms_out):
    assert inlabs_hook._filter_text_terms(text_terms_in) == text_terms_out


@pytest.mark.parametrize(
    "data_in, data_out",
    [
        (
            {
                "texto": ["term1", "term2"],
                "pubname": ["DO1"],
                "pubdate": ["2024-04-01", "2024-04-02"],
            },
            {
                "texto": ["term1", "term2"],
                "pubname": ["DO1E"],
                "pubdate": ["2024-03-31", "2024-04-01"],
            },
        ),
    ],
)
def test_adapt_search_terms_to_extra(inlabs_hook, data_in, data_out):
    assert inlabs_hook._adapt_search_terms_to_extra(data_in) == data_out


def test_map_opensearch_hit_uses_matched_queries(inlabs_hook):
    """Map OpenSearch ``matched_queries`` into matched term fields."""
    hit = {
        "_id": "1",
        "_score": 10.0,
        "_source": {
            "texto_plain": "Aprova as estruturas regimentais da SEGES.",
            "texto": "Aprova as estruturas regimentais da SEGES.",
        },
        "matched_queries": ["estrutura regimental", "SEGES"],
        "highlight": {
            "texto_plain": [
                "Aprova as <%%>estruturas regimentais</%%> da <%%>SEGES</%%>."
            ]
        },
    }

    mapped = inlabs_hook._map_opensearch_hit(
        hit, searched_expression='"estrutura regimental" AND SEGES'
    )

    assert mapped["score"] == 10.0
    assert mapped["searched_expression"] == '"estrutura regimental" AND SEGES'
    assert mapped["matched_terms"] == ["estrutura regimental", "SEGES"]
    assert mapped["matched_terms_text"] == "estrutura regimental, SEGES"
    assert mapped["matches"] == "estrutura regimental, SEGES"
    assert mapped["opensearch_highlights"] == [
        "Aprova as <%%>estruturas regimentais</%%> da <%%>SEGES</%%>."
    ]


def test_map_opensearch_hit_without_matched_queries_returns_empty_terms(inlabs_hook):
    """Return empty matched term fields when a hit has no ``matched_queries``."""
    mapped = inlabs_hook._map_opensearch_hit(
        {"_id": "1", "_score": 1.0, "_source": {"texto": "Sem destaque."}},
        searched_expression="SEGES",
    )

    assert mapped["matched_terms"] == []
    assert mapped["matched_terms_text"] == ""
    assert mapped["matches"] == ""


def test_map_opensearch_hit_semantic_match_flag(inlabs_hook):
    """``semantic_match`` is True only for neural hits with no keyword match."""
    hit_no_keyword = {"_id": "1", "_score": 0.9, "_source": {"texto": "x"}}
    hit_with_keyword = {
        "_id": "2",
        "_score": 9.3,
        "_source": {"texto": "x"},
        "matched_queries": ["SEGES"],
    }

    assert (
        inlabs_hook._map_opensearch_hit(hit_no_keyword, neural_search=True)[
            "semantic_match"
        ]
        is True
    )
    assert (
        inlabs_hook._map_opensearch_hit(hit_with_keyword, neural_search=True)[
            "semantic_match"
        ]
        is False
    )
    assert (
        inlabs_hook._map_opensearch_hit(hit_no_keyword, neural_search=False)[
            "semantic_match"
        ]
        is False
    )


@pytest.mark.parametrize(
    "text_in, text_out",
    [
        ("çãAî  é", "caai  e"),
    ],
)
def test_normalize(inlabs_hook, text_in, text_out):
    assert inlabs_hook.TextDictHandler()._normalize(text_in) == text_out


@pytest.mark.parametrize(
    "pub_name_in, pub_name_out",
    [
        ("DO1", "DOU - Seção 1"),
        ("DO2", "DOU - Seção 2"),
        ("DO3", "DOU - Seção 3"),
        ("DOE", "DOU - Seção  Extra"),
        ("DO1E", "DOU - Seção 1 Extra"),
    ],
)
def test_rename_section(inlabs_hook, pub_name_in, pub_name_out):
    assert inlabs_hook.TextDictHandler()._rename_section(pub_name_in) == pub_name_out


@pytest.mark.parametrize(
    "term, texto_in, texto_out",
    [
        (
            ["elementum"],
            "Pellentesque vel elementum mauris, id semper tellus.",
            "Pellentesque vel <%%>elementum</%%> mauris, id semper tellus.",
        ),
        (
            ["elementum", "tellus"],
            "Pellentesque vel elementum mauris, id semper tellus.",
            "Pellentesque vel <%%>elementum</%%> mauris, id semper <%%>tellus</%%>.",
        ),
        (
            # Term without accent matches accented text (e.g. user searches
            # "Flavia" but DOU publishes "Flávia")
            ["Flavia Teixeira Guerreiro"],
            "Designar Flávia Teixeira Guerreiro para o cargo.",
            "Designar <%%>Flávia Teixeira Guerreiro</%%> para o cargo.",
        ),
        (
            # Term with accent matches non-accented text
            ["Flávia"],
            "Designar Flavia para o cargo.",
            "Designar <%%>Flavia</%%> para o cargo.",
        ),
    ],
)
def test_highlight_terms(inlabs_hook, term, texto_in, texto_out):
    assert inlabs_hook.TextDictHandler()._highlight_terms(term, texto_in) == texto_out


@pytest.mark.parametrize(
    "texto_in, texto_out",
    [
        (  # texto_in
            """
            Lorem ipsum dolor sit amet, consectetur adipiscing elit.
            Phasellus venenatis auctor mauris. Integer id neque quis urna
            ultrices iaculis. Donec et enim mauris. Sed vel massa eget est
            viverra finibus a et magna. Sed ut perspiciatis
            unde omnis iste natus error sit voluptatem accusantium doloremque laudantium,
            totam rem aperiam, eaque ipsa Lorem ipsum dolor sit amet, consectetur adipiscing elit.
            Phasellus venenatis auctor mauris. Integer id neque quis urna
            ultrices iaculis. Donec et enim mauris. Sed vel massa eget est
            viverra finibus a et magna. <%%>Pellentesque</%%> vel elementum
            mauris, id semper tellus. Vivamus convallis lacinia ex sed
            fermentum. Nulla mollis cursus ipsum vel interdum. Mauris
            facilisis posuere elit. Proin consectetur tincidunt urna.
            Cras tincidunt nunc vestibulum velit pellentesque facilisis.
            Aenean sollicitudin ante elit, vitae vehicula nisi congue id.
            Brasília/DF, 15 de março de 2024.  Pessoa 1  Analista
            """,
            # texto_out
            ("""(...) . Sed ut perspiciatis
            unde omnis iste natus error sit voluptatem accusantium doloremque laudantium,
            totam rem aperiam, eaque ipsa Lorem ipsum dolor sit amet, consectetur adipiscing elit.
            Phasellus venenatis auctor mauris. Integer id neque quis urna
            ultrices iaculis. Donec et enim mauris. Sed vel massa eget est
            viverra finibus a et magna. <%%>Pellentesque</%%> vel elementum
            mauris, id semper tellus. Vivamus convallis lacinia ex sed
            fermentum. Nulla mollis cursus ipsum vel interdum. Mauris
            facilisis posuere elit. Proin consectetur tincidunt urna.
            Cras tincidunt nunc vestibulum velit pellentesque facilisis.
            Aenean sollicitudin ante elit, vitae vehicula nisi congue id. (...)"""),
        ),
    ],
)
def test_trim_text(inlabs_hook, texto_in, texto_out):

    assert inlabs_hook.TextDictHandler()._trim_text(texto_in) == texto_out


@pytest.mark.parametrize(
    "texto_in, texto_out",
    [
        (  # texto_in
            """Lorem ipsum dolor sit amet, consectetur adipiscing elit.
            Phasellus venenatis auctor mauris. Integer id neque quis urna
            ultrices iaculis. Donec et enim mauris. Sed vel massa eget est
            viverra finibus a et magna. Sed ut perspiciatis
            unde omnis iste natus error sit voluptatem accusantium doloremque laudantium,
            totam rem aperiam, eaque ipsa <%%>Pellentesque</%%> quae ab illo inventore veritatis et
            quasi architecto beatae vitae dicta sunt explicabo. Nemo enim ipsam
            voluptatem quia voluptas sit aspernatur aut odit aut fugit, sed quia
            consequuntur magni dolores eos qui ratione voluptatem sequi nesciunt.
            Neque porro quisquam est, qui dolorem ipsum quia dolor sit amet, consectetur,
            adipisci velit, sed quia non numquam eius modi tempora incidunt ut labore et
            dolore magnam aliquam quaerat voluptatem.
            """,
            # texto_out
            ("""Lorem ipsum dolor sit amet, consectetur adipiscing elit.
            Phasellus venenatis auctor mauris. Integer id neque quis urna
            ultrices iaculis. Donec et enim mauris. Sed vel massa eget est
            viverra finibus a et magna. Sed ut perspiciatis
            unde omnis iste natus error sit voluptatem accusantium doloremque laudantium,
            totam rem aperiam, eaque ipsa <%%>Pellentesque</%%> quae ab illo inventore veritatis et
            quasi architecto beatae vitae dicta sunt explicabo. Nemo enim ipsam
            voluptatem quia voluptas sit aspernatur aut odit aut fugit, sed quia
            consequuntur magni dolores eos qui ratione voluptatem sequi nesciunt.
            Neque porro quisquam est, qui dolorem ipsum quia dolor sit amet, consectetur,
            adipisci velit, sed quia non numquam eius modi tempora (...)"""),
        ),
    ],
)
def test_trim_text_length(inlabs_hook, texto_in, texto_out):
    assert inlabs_hook.TextDictHandler()._trim_text(texto_in, 450) == texto_out


@pytest.mark.parametrize(
    "texto_in, texto_out",
    [
        (  # texto_in
            """Lorem ipsum dolor sit amet, consectetur adipiscing elit.
            Phasellus venenatis auctor mauris. Integer id neque quis urna
            ultrices iaculis. Donec et enim mauris. Sed vel massa eget est
            viverra finibus a et magna. Sed ut perspiciatis
            unde omnis iste natus error sit voluptatem accusantium doloremque laudantium,
            totam rem aperiam, eaque ipsa <%%>Pellentesque</%%> quae ab illo inventore veritatis et
            quasi architecto beatae vitae dicta sunt explicabo. Nemo enim ipsam
            voluptatem quia voluptas sit aspernatur aut odit aut fugit, sed quia
            consequuntur magni dolores eos qui ratione voluptatem sequi nesciunt.
            Neque porro quisquam est, qui dolorem ipsum quia dolor sit amet, consectetur,
            adipisci velit, sed quia non numquam eius modi tempora incidunt ut labore et
            dolore magnam aliquam quaerat voluptatem.
            """,
            # texto_out
            (
                """(...) d ut perspiciatis
            unde omnis iste natus error sit voluptatem accusantium doloremque laudantium,
            totam rem aperiam, eaque ipsa <%%>Pellentesque</%%> quae ab illo inventore veritatis et
            quasi architecto beatae vitae dicta sunt explicabo. Nemo enim ipsam (...)"""
            ),
        ),
    ],
)
def test_trim_text_length_less_than_400(inlabs_hook, texto_in, texto_out):

    assert inlabs_hook.TextDictHandler()._trim_text(texto_in, 150) == texto_out


@pytest.mark.parametrize(
    "texto_in, texto_out",
    [
        (  # texto_in
            """
            Lorem ipsum dolor sit amet, consectetur adipiscing elit.
            Phasellus venenatis auctor mauris. Integer id neque quis urna
            ultrices iaculis. Donec et enim mauris. Sed vel massa eget est
            viverra finibus a et magna. Sed ut perspiciatis
            unde omnis iste natus error sit voluptatem accusantium doloremque laudantium,
            totam rem aperiam, eaque ipsa Lorem ipsum dolor sit amet, consectetur adipiscing elit.
            Phasellus venenatis auctor mauris. Integer id neque quis urna
            ultrices iaculis. Donec et enim mauris. Sed vel massa eget est
            viverra finibus a et magna. <%%>Pellentesque</%%> vel elementum
            mauris, id semper tellus. Vivamus convallis lacinia ex sed
            fermentum. Nulla mollis cursus ipsum vel interdum. Mauris
            facilisis posuere elit. Proin consectetur tincidunt urna.
            Cras tincidunt nunc vestibulum velit pellentesque facilisis.
            Aenean sollicitudin ante elit, vitae vehicula nisi congue id.
            Brasília/DF, 15 de março de 2024.  Pessoa 1  Analista
            """,
            # texto_out
            ("""(...) . Sed ut perspiciatis
            unde omnis iste natus error sit voluptatem accusantium doloremque laudantium,
            totam rem aperiam, eaque ipsa Lorem ipsum dolor sit amet, consectetur adipiscing elit.
            Phasellus venenatis auctor mauris. Integer id neque quis urna
            ultrices iaculis. Donec et enim mauris. Sed vel massa eget est
            viverra finibus a et magna. <%%>Pellentesque</%%> vel elementum
            mauris, id semper tellus. Vivamus convallis lacinia ex sed
            fermentum. Nulla mollis cursus ipsum vel interdum. Mauris
            facilisis posuere elit. Proin consectetur tincidunt urna.
            Cras tincidunt nunc vestibulum velit pellentesque facilisis.
            Aenean sollicitudin ante elit, vitae vehicula nisi congue id. (...)"""),
        ),
    ],
)
def test_trim_text_length_less_than_0(inlabs_hook, texto_in, texto_out):
    assert inlabs_hook.TextDictHandler()._trim_text(texto_in, -1) == texto_out


@pytest.mark.parametrize(
    "df_in, dict_out",
    [
        (
            # df_in
            pd.DataFrame(
                [
                    {
                        "title": "Título da Publicação 1",
                        "href": "http://xxx.gov.br/",
                        "date": "2024-03-15",
                        "section": "DO1",
                        "abstract": "Lorem ipsum dolor sit amet.",
                        "matches": "Lorem",
                    },
                    {
                        "title": "Título da Publicação 2",
                        "href": "http://xxx.gov.br/",
                        "date": "2024-03-15",
                        "section": "DO1",
                        "abstract": "Pellentesque vel elementum mauris.",
                        "matches": "Pellentesque",
                    },
                    {
                        "title": "Título da Publicação 3",
                        "href": "http://xxx.gov.br/",
                        "date": "2024-03-15",
                        "section": "DO1",
                        "abstract": "Dolor sit amet, lórem consectetur adipiscing elit.",
                        "matches": "Lorem",
                    },
                ]
            ),
            # dict_out
            {
                "Lorem": [
                    {
                        "title": "Título da Publicação 1",
                        "href": "http://xxx.gov.br/",
                        "date": "2024-03-15",
                        "section": "DO1",
                        "abstract": "Lorem ipsum dolor sit amet.",
                    },
                    {
                        "title": "Título da Publicação 3",
                        "href": "http://xxx.gov.br/",
                        "date": "2024-03-15",
                        "section": "DO1",
                        "abstract": "Dolor sit amet, lórem consectetur adipiscing elit.",
                    },
                ],
                "Pellentesque": [
                    {
                        "title": "Título da Publicação 2",
                        "href": "http://xxx.gov.br/",
                        "date": "2024-03-15",
                        "section": "DO1",
                        "abstract": "Pellentesque vel elementum mauris.",
                    }
                ],
            },
        ),
    ],
)
def test_group_to_dict(inlabs_hook, df_in, dict_out):
    cols = [
        "section",
        "title",
        "href",
        "abstract",
        "date",
    ]
    r = inlabs_hook.TextDictHandler()._group_to_dict(df_in, "matches", cols)

    assert r == dict_out


def _terms_from_group(group_name):
    """Convert a grouped matches key into a list of matched terms."""
    return [term for term in group_name.split(", ") if term]


def _add_matched_terms_from_expected(df_in, expected):
    """Add fake OpenSearch matched terms to old transform fixtures."""
    id_to_terms = {}
    for group_name, items in expected.items():
        for item in items:
            id_to_terms[item["id"]] = _terms_from_group(group_name)

    df = df_in.copy()
    df["matched_terms"] = df["id"].apply(lambda row_id: id_to_terms.get(row_id, []))
    return df


def _add_matched_terms_to_expected(expected):
    """Add matched term fields expected in transformed output fixtures."""
    updated = copy.deepcopy(expected)
    for group_name, items in updated.items():
        terms = _terms_from_group(group_name)
        for item in items:
            item["matched_terms"] = terms
            item["matched_terms_text"] = ", ".join(terms)
    return updated


@pytest.mark.parametrize(
    "terms, df_in, dict_out, full_text, use_summary, has_ementa, show_relevancy",
    [
        (
            ["Pellentesque", "Lorem"],
            pd.DataFrame(
                [
                    {
                        "artcategory": "Texto exemplo art_category",
                        "arttype": "Publicação xxx",
                        "id": 1,
                        "assina": "Pessoa 1",
                        "data": "Brasília/DF, 15 de março de 2024.",
                        "ementa": "None",
                        "identifica": "Título da Publicação 1",
                        "name": "15.03.2024 bsb DOU xxx",
                        "pdfpage": "http://xxx.gov.br/",
                        "pubdate": datetime(2024, 3, 15),
                        "pubname": "DO1",
                        "subtitulo": "None",
                        "texto": "Lorem ipsum dolor sit amet.",
                        "titulo": "None",
                    },
                    {
                        "artcategory": "Texto exemplo art_category",
                        "arttype": "Publicação xxx",
                        "id": 2,
                        "assina": "Pessoa 2",
                        "data": "Brasília/DF, 15 de março de 2024.",
                        "ementa": "None",
                        "identifica": "Título da Publicação 2",
                        "name": "15.03.2024 bsb DOU xxx",
                        "pdfpage": "http://xxx.gov.br/",
                        "pubdate": datetime(2024, 3, 15),
                        "pubname": "DO1",
                        "subtitulo": "None",
                        "texto": "Dolor sit amet, consectetur adipiscing elit. Pellentesque.",
                        "titulo": "None",
                    },
                ]
            ),
            {
                "Lorem": [
                    {
                        "section": "DOU - Seção 1",
                        "title": "TÍTULO DA PUBLICAÇÃO 1",
                        "href": "http://xxx.gov.br/",
                        "abstract": "<%%>Lorem</%%> ipsum dolor sit amet.",
                        "date": "15/03/2024",
                        "id": 1,
                        "display_date_sortable": None,
                        "hierarchyList": "Texto exemplo art_category",
                        "ai_generated": False,
                        "has_ementa": False,
                        "full_text": False,
                        "score": None,
                        "show_relevancy": False,
                        "semantic_match": False,
                    }
                ],
                "Pellentesque": [
                    {
                        "section": "DOU - Seção 1",
                        "title": "TÍTULO DA PUBLICAÇÃO 2",
                        "href": "http://xxx.gov.br/",
                        "abstract": "Dolor sit amet, consectetur adipiscing elit. <%%>Pellentesque</%%>.",
                        "date": "15/03/2024",
                        "id": 2,
                        "display_date_sortable": None,
                        "hierarchyList": "Texto exemplo art_category",
                        "ai_generated": False,
                        "has_ementa": False,
                        "full_text": False,
                        "score": None,
                        "show_relevancy": False,
                        "semantic_match": False,
                    }
                ],
            },
            False,
            False,
            False,
            False,
        ),
        (
            ["Lorem"],
            pd.DataFrame(
                [
                    {
                        "artcategory": "Texto exemplo art_category",
                        "arttype": "Publicação xxx",
                        "id": 1,
                        "assina": "Pessoa 1",
                        "data": "Brasília/DF, 15 de março de 2024.",
                        "ementa": "None",
                        "identifica": "Título da Publicação 1",
                        "name": "15.03.2024 bsb DOU xxx",
                        "pdfpage": "http://xxx.gov.br/",
                        "pubdate": datetime(2024, 3, 15),
                        "pubname": "DO1",
                        "subtitulo": "None",
                        "texto": """Lorem ipsum dolor sit amet, consectetur adipiscing elit.
                        Phasellus venenatis auctor mauris. Integer id neque quis urna
                        ultrices iaculis. Donec et enim mauris. Sed vel massa eget est
                        viverra finibus a et magna. Pellentesque vel elementum
                        mauris, id semper tellus. Vivamus convallis lacinia ex sed
                        fermentum. Nulla mollis cursus ipsum vel interdum. Mauris
                        facilisis posuere elit. Proin consectetur tincidunt urna.
                        Cras tincidunt nunc vestibulum velit pellentesque facilisis.
                        Aenean sollicitudin ante elit, vitae vehicula nisi congue id.
                        Brasília/DF, 15 de março de 2024.  Pessoa 1  Analista
                        """,
                        "titulo": "None",
                    },
                ]
            ),
            {
                "Lorem": [
                    {
                        "section": "DOU - Seção 1",
                        "title": "TÍTULO DA PUBLICAÇÃO 1",
                        "href": "http://xxx.gov.br/",
                        "abstract": (
                            "<%%>Lorem</%%> ipsum dolor sit amet, consectetur adipiscing elit.\n"
                            "                        Phasellus venenatis auctor mauris. Integer id neque quis urna\n"
                            "                        ultrices iaculis. Donec et enim mauris. Sed vel massa eget est\n"
                            "                        viverra finibus a et magna. Pellentesque vel elementum\n"
                            "                        mauris, id semper tellus. Vivamus convallis lacinia ex sed\n"
                            "                        fermentum. Nulla mollis cursus ipsum vel interdum. Mauris\n"
                            "                        facilisis posuere elit. Proin consectetur tincidunt urna.\n"
                            "                        Cras tincidunt nunc vestibulum velit pellentesque facilisis.\n"
                            "                        Aenean sollicitudin ante elit, vitae vehicula nisi congue id.\n"
                            "                        Brasília/DF, 15 de março de 2024.  Pessoa 1  Analista\n"
                            "                        "
                        ),
                        "date": "15/03/2024",
                        "id": 1,
                        "display_date_sortable": None,
                        "hierarchyList": "Texto exemplo art_category",
                        "ai_generated": False,
                        "has_ementa": False,
                        "full_text": True,
                        "score": None,
                        "show_relevancy": False,
                        "semantic_match": False,
                    }
                ],
            },
            True,
            False,
            False,
            False,
        ),
        (
            ["Lorem"],
            pd.DataFrame(
                [
                    {
                        "artcategory": "Texto exemplo art_category",
                        "arttype": "Publicação xxx",
                        "id": 1,
                        "assina": "Pessoa 1",
                        "data": "Brasília/DF, 15 de março de 2024.",
                        "ementa": """Integer id neque quis urna ultrices iaculis.
                        Donec et enim mauris""",
                        "identifica": "Título da Publicação 1",
                        "name": "15.03.2024 bsb DOU xxx",
                        "pdfpage": "http://xxx.gov.br/",
                        "pubdate": datetime(2024, 3, 15),
                        "pubname": "DO1",
                        "subtitulo": "None",
                        "texto": """Lorem ipsum dolor sit amet, consectetur adipiscing elit.
                        Phasellus venenatis auctor mauris. Integer id neque quis urna
                        ultrices iaculis. Donec et enim mauris. Sed vel massa eget est
                        viverra finibus a et magna. Pellentesque vel elementum
                        mauris, id semper tellus. Vivamus convallis lacinia ex sed
                        fermentum. Nulla mollis cursus ipsum vel interdum. Mauris
                        facilisis posuere elit. Proin consectetur tincidunt urna.
                        Cras tincidunt nunc vestibulum velit pellentesque facilisis.
                        Aenean sollicitudin ante elit, vitae vehicula nisi congue id.
                        Brasília/DF, 15 de março de 2024.  Pessoa 1  Analista
                        """,
                        "titulo": "None",
                    },
                ]
            ),
            {
                "Lorem": [
                    {
                        "section": "DOU - Seção 1",
                        "title": "TÍTULO DA PUBLICAÇÃO 1",
                        "href": "http://xxx.gov.br/",
                        "abstract": """Integer id neque quis urna ultrices iaculis.
                        Donec et enim mauris""",
                        "date": "15/03/2024",
                        "id": 1,
                        "display_date_sortable": None,
                        "hierarchyList": "Texto exemplo art_category",
                        "ai_generated": False,
                        "has_ementa": True,
                        "full_text": True,
                        "score": None,
                        "show_relevancy": False,
                        "semantic_match": False,
                    }
                ],
            },
            True,
            True,
            False,
            False,
        ),
        # HTML texto with identifica tag — title must not appear in abstract
        (
            ["Lorem"],
            pd.DataFrame(
                [
                    {
                        "artcategory": "Texto exemplo art_category",
                        "arttype": "Publicação xxx",
                        "id": 1,
                        "assina": "Pessoa 1",
                        "data": "Brasília/DF, 15 de março de 2024.",
                        "ementa": "None",
                        "identifica": "Título da Publicação 1",
                        "name": "15.03.2024 bsb DOU xxx",
                        "pdfpage": "http://xxx.gov.br/",
                        "pubdate": datetime(2024, 3, 15),
                        "pubname": "DO1",
                        "subtitulo": "None",
                        "texto": '<p class="identifica">Título da Publicação 1</p><p>Lorem ipsum dolor sit amet.</p>',
                        "titulo": "None",
                    },
                ]
            ),
            {
                "Lorem": [
                    {
                        "section": "DOU - Seção 1",
                        "title": "TÍTULO DA PUBLICAÇÃO 1",
                        "href": "http://xxx.gov.br/",
                        "abstract": "<p><%%>Lorem</%%> ipsum dolor sit amet.</p>",
                        "date": "15/03/2024",
                        "id": 1,
                        "display_date_sortable": None,
                        "hierarchyList": "Texto exemplo art_category",
                        "ai_generated": False,
                        "has_ementa": False,
                        "full_text": False,
                        "score": None,
                        "show_relevancy": False,
                        "semantic_match": False,
                    }
                ],
            },
            False,
            False,
            False,
            False,
        ),
        # No terms
        (
            [],
            pd.DataFrame(
                [
                    {
                        "artcategory": "Texto exemplo art_category",
                        "arttype": "Publicação xxx",
                        "id": 1,
                        "assina": "Pessoa 1",
                        "data": "Brasília/DF, 15 de março de 2024.",
                        "ementa": "None",
                        "identifica": "Título da Publicação 1",
                        "name": "15.03.2024 bsb DOU xxx",
                        "pdfpage": "http://xxx.gov.br/",
                        "pubdate": datetime(2024, 3, 15),
                        "pubname": "DO1",
                        "subtitulo": "None",
                        "texto": """Lorem ipsum dolor sit amet, consectetur adipiscing elit.
                        Phasellus venenatis auctor mauris. Integer id neque quis urna
                        ultrices iaculis. Donec et enim mauris. Sed vel massa eget est
                        viverra finibus a et magna. Pellentesque vel elementum
                        mauris, id semper tellus. Vivamus convallis lacinia ex sed
                        fermentum. Nulla mollis cursus ipsum vel interdum. Mauris
                        facilisis posuere elit. Proin consectetur tinc
                        """,
                        "titulo": "None",
                    },
                ]
            ),
            {
                "": [
                    {
                        "section": "DOU - Seção 1",
                        "title": "TÍTULO DA PUBLICAÇÃO 1",
                        "href": "http://xxx.gov.br/",
                        "abstract": (
                            "Lorem ipsum dolor sit amet, consectetur adipiscing elit.\n"
                            "                        Phasellus venenatis auctor mauris. Integer id neque quis urna\n"
                            "                        ultrices iaculis. Donec et enim mauris. Sed vel massa eget est\n"
                            "                        viverra finibus a et magna. Pellentesque vel elementum\n"
                            "                        mauris, id semper tellus. Vivamus convallis lacinia ex sed (...)"
                        ),
                        "date": "15/03/2024",
                        "id": 1,
                        "display_date_sortable": None,
                        "hierarchyList": "Texto exemplo art_category",
                        "ai_generated": False,
                        "has_ementa": False,
                        "full_text": False,
                        "score": None,
                        "show_relevancy": True,
                        "semantic_match": False,
                    }
                ],
            },
            False,
            False,
            False,
            True,
        ),
    ],
)
def test_transform_search_results(
    inlabs_hook, terms, df_in, dict_out, full_text, use_summary, has_ementa, show_relevancy
):
    """Transform results using matched terms supplied by OpenSearch hits."""
    if terms:
        df_in = _add_matched_terms_from_expected(df_in, dict_out)
        dict_out = _add_matched_terms_to_expected(dict_out)

    r = inlabs_hook.TextDictHandler().transform_search_results(
        ai_config=_MIN_AI_CONFIG,
        response=df_in,
        text_terms=terms,
        ignore_signature_match=False,
        ai_search_config=_MIN_AI_SEARCH_CONFIG,
        full_text=full_text,
        text_length=400,
        use_summary=use_summary,
        has_ementa=has_ementa,
        show_relevancy=show_relevancy,
    )
    assert r == dict_out


def test_transform_search_results_forces_show_relevancy_for_neural_search(inlabs_hook):
    """Semantic hits may have no matched_terms, so relevancy must stay visible."""
    df_in = pd.DataFrame(
        [
            {
                "artcategory": "Texto exemplo art_category",
                "arttype": "Publicação xxx",
                "id": 1,
                "assina": "Pessoa 1",
                "data": "Brasília/DF, 15 de março de 2024.",
                "ementa": "None",
                "identifica": "Título da Publicação 1",
                "name": "15.03.2024 bsb DOU xxx",
                "pdfpage": "http://xxx.gov.br/",
                "pubdate": datetime(2024, 3, 15),
                "pubname": "DO1",
                "subtitulo": "None",
                "texto": "Lorem ipsum dolor sit amet.",
                "titulo": "None",
            },
        ]
    )

    r = inlabs_hook.TextDictHandler().transform_search_results(
        ai_config=_MIN_AI_CONFIG,
        response=df_in,
        text_terms=[],
        ignore_signature_match=False,
        ai_search_config=_MIN_AI_SEARCH_CONFIG,
        show_relevancy=False,
        neural_search=True,
    )

    assert r[""][0]["show_relevancy"] is True


def test_search_text_propagates_neural_search_flag(monkeypatch, inlabs_hook):
    """``neural_search_config`` must reach the generated OpenSearch query payload."""
    monkeypatch.setattr(
        "dags.ro_dou_src.hooks.inlabs_hook.RO_DOU_INLABS_USE_OPENSEARCH", "true"
    )

    seen_payloads = []

    def fake_generate_query(payload):
        seen_payloads.append(payload)
        return {}

    monkeypatch.setattr(
        inlabs_hook, "_generate_opensearch_query", fake_generate_query
    )

    fake_client = MagicMock()
    fake_client.search.return_value = {"hits": {"hits": []}}

    result = inlabs_hook.search_text(
        ai_config=_MIN_AI_CONFIG,
        ai_search_config=_MIN_AI_SEARCH_CONFIG,
        search_terms={
            "texto": ["estrutura regimental"],
            "pubdate": ["2024-04-01"],
            "pubname": ["DO1"],
        },
        ignore_signature_match=False,
        full_text=False,
        text_length=400,
        use_summary=False,
        show_relevancy=False,
        neural_search_config=NeuralSearchConfig(neural_search=True, score=0.9),
        client=fake_client,
    )

    assert result == {}
    assert all(payload.get("neural_search") is True for payload in seen_payloads)
    assert all(payload.get("min_score") == 0.9 for payload in seen_payloads)


@pytest.mark.parametrize(
    "terms, df_in, dict_out, has_ementa, full_text",
    [
        (  # terms
            ["Pellentesque", "Pessoa 1"],
            # df_in
            pd.DataFrame(
                [
                    {
                        "artcategory": "Texto exemplo art_category",
                        "arttype": "Publicação xxx",
                        "id": 1,
                        "assina": "Pessoa 1",
                        "data": "Brasília/DF, 15 de março de 2024.",
                        "ementa": "None",
                        "identifica": "Título da Publicação",
                        "name": "15.03.2024 bsb DOU xxx",
                        "pdfpage": "http://xxx.gov.br/",
                        "pubdate": datetime(2024, 3, 15),
                        "pubname": "DO1",
                        "subtitulo": "None",
                        "texto": "Pessoa 1 ipsum dolor sit amet.",
                        "titulo": "None",
                    },
                    {
                        "artcategory": "Texto exemplo art_category",
                        "arttype": "Publicação xxx",
                        "id": 2,
                        "assina": "Pessoa 2",
                        "data": "Brasília/DF, 15 de março de 2024.",
                        "ementa": "None",
                        "identifica": "Título da Publicação",
                        "name": "15.03.2024 bsb DOU xxx",
                        "pdfpage": "http://xxx.gov.br/",
                        "pubdate": datetime(2024, 3, 15),
                        "pubname": "DO1",
                        "subtitulo": "None",
                        "texto": "Pellentesque Phasellus venenatis auctor mauris.",
                        "titulo": "None",
                    },
                ]
            ),
            # dict_out
            {
                "Pellentesque": [
                    {
                        "section": "DOU - Seção 1",
                        "title": "TÍTULO DA PUBLICAÇÃO",
                        "href": "http://xxx.gov.br/",
                        "abstract": "<%%>Pellentesque</%%> Phasellus venenatis auctor mauris.",
                        "date": "15/03/2024",
                        "id": 2,
                        "display_date_sortable": None,
                        "hierarchyList": "Texto exemplo art_category",
                        "ai_generated": False,
                        "has_ementa": False,
                        "full_text": False,
                        "score": None,
                        "show_relevancy": False,
                        "semantic_match": False,
                    }
                ]
            },
            False,
            False,
        )
    ],
)
def test_ignore_signature(inlabs_hook, terms, df_in, dict_out, has_ementa, full_text):
    """Ignore signature-only matches using OpenSearch matched terms."""
    df_in = df_in.copy()
    df_in["matched_terms"] = [["Pessoa 1"], ["Pellentesque"]]
    dict_out = _add_matched_terms_to_expected(dict_out)

    r = inlabs_hook.TextDictHandler().transform_search_results(
        ai_config=_MIN_AI_CONFIG,
        ai_search_config=_MIN_AI_SEARCH_CONFIG,
        has_ementa=has_ementa,
        full_text=full_text,
        response=df_in,
        text_terms=terms,
        ignore_signature_match=True,
        show_relevancy=False,
    )
    assert r == dict_out


@pytest.mark.parametrize(
    "abstract, result",
    [
        (
            """<p class="identifica">Título da Publicação </p><p class='subtitulo'>Lorem ipsum.</p><p>Lorem ipsum dolor sit amet, consectetur adipiscing elit.</p>""",
            """<p class="subtitulo">Lorem ipsum.</p><p>Lorem ipsum dolor sit amet, consectetur adipiscing elit.</p>""",
        )
    ],
)
def test_remove_duplicated_title(inlabs_hook, abstract, result):
    assert inlabs_hook.TextDictHandler()._remove_duplicated_title(abstract) == result



@pytest.mark.parametrize(
    "abstract, result",
    [
        (
            """
            <table>
                <tr></tr>
                <tr>
                    <td colspan="1" rowspan="1">
                        <p>QTD.</p>
                    </td>
                    <td colspan="1" rowspan="1">
                        <p>NOME</p>
                    </td>
                </tr>
                <tr>
                    <td colspan="1" rowspan="1">
                        <p>01</p>
                    </td>
                    <td colspan="1" rowspan="1">
                        <p>ANDREA COSTA CHAVES</p>
                    </td>
                </tr>
            </table>
            """,
            """
            <table>
                <tr>
                    <td colspan="1" rowspan="1">
                        <p>QTD.</p>
                    </td>
                    <td colspan="1" rowspan="1">
                        <p>NOME</p>
                    </td>
                </tr>
                <tr>
                    <td colspan="1" rowspan="1">
                        <p>01</p>
                    </td>
                    <td colspan="1" rowspan="1">
                        <p>ANDREA COSTA CHAVES</p>
                    </td>
                </tr>
            </table>
            """,
        )
    ],
)
def test_remove_empty_tr(inlabs_hook, abstract, result):
    from bs4 import BeautifulSoup

    assert BeautifulSoup(
        inlabs_hook.TextDictHandler()._remove_empty_tr(abstract), "html.parser"
    ) == BeautifulSoup(result, "html.parser")


@pytest.mark.parametrize(
    "text, expected",
    [
        ("hello world", 11),
        ("<b>hello</b> world", 11),
        ("<%%>termo</%%>", 5),
        ("<p class='x'>abc</p>", 3),
        ("sem tags", 8),
        ("", 0),
    ],
)
def test_visible_len(inlabs_hook, text, expected):
    assert inlabs_hook.TextDictHandler()._visible_len(text) == expected


@pytest.mark.parametrize(
    "text, n, expected_visible",
    [
        ("abcdef", 3, 3),
        ("<b>abc</b>def", 3, 3),  # tags não contam, retém tag completa
        ("<%%>ab</%%>cde", 4, 4),  # marcadores de destaque não contam
        ("abc", 10, 3),  # n maior que o texto: retorna tudo
        ("", 5, 0),
    ],
)
def test_cut_visible_start_visible_len(inlabs_hook, text, n, expected_visible):
    H = inlabs_hook.TextDictHandler()
    result = H._cut_visible_start(text, n)
    assert H._visible_len(result) == expected_visible


@pytest.mark.parametrize(
    "text, n, expected",
    [
        # tag HTML preservada no resultado
        ("<b>hello</b> world", 7, "<b>hello</b> w"),
        # marcador <%%> preservado
        ("<%%>abc</%%> def", 5, "<%%>abc</%%> d"),
    ],
)
def test_cut_visible_start_preserves_tags(inlabs_hook, text, n, expected):
    assert inlabs_hook.TextDictHandler()._cut_visible_start(text, n) == expected


@pytest.mark.parametrize(
    "text, n, expected_visible",
    [
        ("abcdef", 3, 3),
        ("abc<b>def</b>", 3, 3),  # tags não contam, retém tag completa
        ("ab<%%>cd</%%>ef", 4, 4),
        ("abc", 10, 3),  # n maior que o texto: retorna tudo
        ("", 5, 0),
    ],
)
def test_cut_visible_end_visible_len(inlabs_hook, text, n, expected_visible):
    H = inlabs_hook.TextDictHandler()
    result = H._cut_visible_end(text, n)
    assert H._visible_len(result) == expected_visible


@pytest.mark.parametrize(
    "text, n, expected",
    [
        # tag HTML preservada no resultado
        ("hello <b>world</b>", 7, "o <b>world</b>"),
        # marcador <%%> preservado
        ("abc <%%>def</%%>", 5, "c <%%>def</%%>"),
    ],
)
def test_cut_visible_end_preserves_tags(inlabs_hook, text, n, expected):
    assert inlabs_hook.TextDictHandler()._cut_visible_end(text, n) == expected


@pytest.mark.parametrize(
    "text, text_length, expected_text, expected_cut",
    [
        # sem tags: comportamento original
        ("abcde fghij", 5, "abcde", True),
        ("abc", 10, "abc", False),
        # tags não contam: "<b>abc</b> de" → visível "abc de" (6 chars)
        # limite 5 → deve cortar após 5 chars visíveis, preservando a tag
        ("<b>abc</b> de", 5, "<b>abc</b>", True),
        # marcador <%%> não conta
        ("<%%>abc</%%> def ghi", 6, "<%%>abc</%%> def", True),
        # texto com tabela HTML: tabela não entra na contagem e é preservada inteira
        ("ab <table><tr><td>x</td></tr></table> cd", 2, "ab", True),
    ],
)
def test_truncate_from_start(
    inlabs_hook, text, text_length, expected_text, expected_cut
):
    result, was_cut = inlabs_hook.TextDictHandler()._truncate_from_start(
        text, text_length
    )

    assert result == expected_text
    assert was_cut == expected_cut



@pytest.mark.parametrize(
    "text, text_length, expected_text, expected_cut",
    [
        # sem tags: comportamento original
        ("abcde fghij", 5, "fghij", True),
        ("abc", 10, "abc", False),
        # tags não contam
        ("ab <b>cde</b>", 5, "b <b>cde</b>", True),
        # marcador <%%> não conta
        ("abc <%%>def</%%> ghi", 6, "<%%>def</%%> ghi", True),
        # tabela preservada inteira e não contada
        (
            "ab <table><tr><td>x</td></tr></table> cd",
            2,
            "<table><tr><td>x</td></tr></table>cd",
            True,
        ),
    ],
)
def test_truncate_from_end(inlabs_hook, text, text_length, expected_text, expected_cut):
    result, was_cut = inlabs_hook.TextDictHandler()._truncate_from_end(
        text, text_length
    )

    assert result == expected_text
    assert was_cut == expected_cut


def _sample_row(**overrides):
    base = {
        "artcategory": "Texto exemplo art_category",
        "arttype": "Publicação xxx",
        "id": 1,
        "assina": None,
        "data": "Brasília/DF, 15 de março de 2024.",
        "ementa": "None",
        "identifica": "Título da Publicação",
        "name": "15.03.2024 bsb DOU xxx",
        "pdfpage": "http://xxx.gov.br/",
        "pubdate": datetime(2024, 3, 15),
        "pubname": "DO1",
        "subtitulo": "None",
        "texto": "Lorem ipsum dolor sit amet, conteúdo suficiente para o teste.",
        "titulo": "None",
    }
    base.update(overrides)
    return base


def test_transform_search_results_uses_opensearch_highlight_for_morphological_variant(
    inlabs_hook,
):
    """Center the excerpt on the actual variant highlighted by OpenSearch."""
    df = pd.DataFrame(
        [
            _sample_row(
                texto=(
                    "Texto inicial distante. " * 20
                    + "Aprova as estruturas regimentais da SEGES."
                ),
                matched_terms=["estrutura regimental"],
                opensearch_highlights=[
                    "Aprova as <%%>estruturas regimentais</%%> da SEGES."
                ],
            )
        ]
    )

    result = inlabs_hook.TextDictHandler().transform_search_results(
        ai_config=_MIN_AI_CONFIG,
        ai_search_config=_MIN_AI_SEARCH_CONFIG,
        response=df,
        text_terms=["estrutura regimental"],
        ignore_signature_match=False,
        full_text=False,
        text_length=20,
    )

    item = result["estrutura regimental"][0]
    assert item["abstract"] == (
        "Aprova as <%%>estruturas regimentais</%%> da SEGES."
    )
    assert item["matched_terms"] == ["estrutura regimental"]
    assert item["matched_terms_text"] == "estrutura regimental"


def test_transform_search_results_prefers_local_highlight_over_broad_opensearch_tokens(
    inlabs_hook,
):
    """Avoid highlighting extra analyzer tokens when the configured term exists."""
    df = pd.DataFrame(
        [
            _sample_row(
                texto=(
                    "MINISTERIO DA GESTAO E DA INOVACAO EM SERVICOS PUBLICOS "
                    "publica ato sobre GSISTE no Sistema de Pessoal Civil."
                ),
                matched_terms=["GSISTE"],
                opensearch_highlights=[
                    (
                        "MINISTERIO DA <%%>GESTAO</%%> E DA INOVACAO EM SERVICOS "
                        "PUBLICOS publica ato sobre <%%>GSISTE</%%> no Sistema "
                        "<%%>de</%%> Pessoal Civil."
                    )
                ],
            )
        ]
    )

    result = inlabs_hook.TextDictHandler().transform_search_results(
        ai_config=_MIN_AI_CONFIG,
        ai_search_config=_MIN_AI_SEARCH_CONFIG,
        response=df,
        text_terms=["GSISTE"],
        ignore_signature_match=False,
        full_text=False,
        text_length=400,
    )

    item = result["GSISTE"][0]
    assert item["abstract"] == (
        "MINISTERIO DA GESTAO E DA INOVACAO EM SERVICOS PUBLICOS publica ato "
        "sobre <%%>GSISTE</%%> no Sistema de Pessoal Civil."
    )


def test_transform_search_results_ai_respects_pub_limit(inlabs_hook):
    df = pd.DataFrame(
        [
            _sample_row(id=1, texto="Lorem " * 30, has_ementa=False, full_text=False),
            _sample_row(
                id=2,
                identifica="Título 2",
                texto="Lorem " * 30,
                has_ementa=False,
                full_text=False,
            ),
            _sample_row(
                id=3,
                identifica="Título 3",
                texto="Lorem " * 30,
                has_ementa=False,
                full_text=False,
            ),
        ]
    )
    ai_search_config = AISearchConfig(
        use_ai_summary=True,
        ai_pub_limit=3,
    )
    with patch(f"{_INLABS_HOOK}.Variable.get", return_value="sk-fake"):
        with patch(f"{_INLABS_HOOK}.AIRunner.run", return_value="Resumo.") as mock_run:
            inlabs_hook.TextDictHandler().transform_search_results(
                ai_config=_MIN_AI_CONFIG,
                ai_search_config=ai_search_config,
                response=df,
                text_terms=["Lorem"],
                ignore_signature_match=False,
                full_text=False,
            )
    assert mock_run.call_count == 3


def test_transform_search_results_ai_system_prompt_uses_matches(inlabs_hook):
    """Use OpenSearch matched terms when formatting the AI system prompt."""
    df = pd.DataFrame(
        [_sample_row(has_ementa=False, full_text=False, matched_terms=["Lorem"])]
    )
    ai_search_config = AISearchConfig(
        use_ai_summary=True,
        ai_custom_prompt="Enfatize {} na análise",
    )
    with patch(f"{_INLABS_HOOK}.Variable.get", return_value="sk-fake"):
        with patch(f"{_INLABS_HOOK}.AIRunner.run", return_value="Resumo.") as mock_run:
            inlabs_hook.TextDictHandler().transform_search_results(
                ai_config=_MIN_AI_CONFIG,
                ai_search_config=ai_search_config,
                response=df,
                text_terms=["Lorem"],
                ignore_signature_match=False,
                full_text=False,
            )
    mock_run.assert_called_once()
    kwargs = mock_run.call_args.kwargs
    assert kwargs["system_prompt"] == "Enfatize Lorem na análise"
    assert kwargs["provider"] == AIProvider.openai
    assert kwargs["model"] == "gpt-4o-mini"


def test_transform_search_results_highlights_term_in_summary(inlabs_hook):
    """Highlight matched terms when `use_summary` replaces text with ementa."""
    df = pd.DataFrame(
        [
            _sample_row(
                ementa="Resumo cita Lorem no clipping.",
                texto="Corpo original com Lorem.",
                matched_terms=["Lorem"],
            )
        ]
    )

    out = inlabs_hook.TextDictHandler().transform_search_results(
        ai_config=_MIN_AI_CONFIG,
        ai_search_config=_MIN_AI_SEARCH_CONFIG,
        response=df,
        text_terms=["Lorem"],
        ignore_signature_match=False,
        use_summary=True,
        full_text=False,
    )

    item = out["Lorem"][0]
    assert item["abstract"] == "Resumo cita <%%>Lorem</%%> no clipping."


def test_transform_search_results_highlights_term_in_ai_summary(inlabs_hook):
    """Highlight matched terms when AI summary returns them in final clipping."""
    df = pd.DataFrame(
        [
            _sample_row(
                texto="Corpo original com Lorem.",
                matched_terms=["Lorem"],
            )
        ]
    )
    ai_search_config = AISearchConfig(use_ai_summary=True)

    with patch(f"{_INLABS_HOOK}.Variable.get", return_value="sk-fake"):
        with patch(
            f"{_INLABS_HOOK}.AIRunner.run",
            return_value="Resumo IA cita Lorem no clipping.",
        ):
            out = inlabs_hook.TextDictHandler().transform_search_results(
                ai_config=_MIN_AI_CONFIG,
                ai_search_config=ai_search_config,
                response=df,
                text_terms=["Lorem"],
                ignore_signature_match=False,
                full_text=False,
            )

    item = out["Lorem"][0]
    assert item["abstract"] == "Resumo IA cita <%%>Lorem</%%> no clipping."
    assert item["ai_generated"] is True


def test_transform_search_results_ai_only_where_ementa_missing_with_use_summary(
    inlabs_hook,
):
    df = pd.DataFrame(
        [
            _sample_row(
                id=1,
                identifica="Com ementa",
                ementa="Resumo já existente.",
                texto="Lorem corpo original.",
                has_ementa=True,
                full_text=False,
            ),
            _sample_row(
                id=2,
                identifica="Sem ementa",
                ementa=np.nan,
                texto="Lorem precisa de IA aqui.",
            ),
        ]
    )
    ai_search_config = AISearchConfig(
        use_ai_summary=True,
        ai_pub_limit=3,
    )
    with patch(f"{_INLABS_HOOK}.Variable.get", return_value="sk-fake"):
        with patch(
            f"{_INLABS_HOOK}.AIRunner.run", return_value="Resumo IA."
        ) as mock_run:
            inlabs_hook.TextDictHandler().transform_search_results(
                ai_config=_MIN_AI_CONFIG,
                ai_search_config=ai_search_config,
                response=df,
                text_terms=["Lorem"],
                ignore_signature_match=False,
                use_summary=True,
                full_text=False,
            )
    assert mock_run.call_count == 1
    kwargs = mock_run.call_args.kwargs
    assert "Lorem" in kwargs["input_text"]


def test_transform_search_results_ai_sets_ai_generated_flag(inlabs_hook):
    df = pd.DataFrame([_sample_row(has_ementa=False, full_text=False)])
    ai_search_config = AISearchConfig(use_ai_summary=True)
    with patch(f"{_INLABS_HOOK}.Variable.get", return_value="sk-fake"):
        with patch(f"{_INLABS_HOOK}.AIRunner.run", return_value="Texto só da IA."):
            out = inlabs_hook.TextDictHandler().transform_search_results(
                ai_config=_MIN_AI_CONFIG,
                ai_search_config=ai_search_config,
                response=df,
                text_terms=["Lorem"],
                ignore_signature_match=False,
                full_text=False,
            )
    items = [item for group in out.values() for item in group]
    assert len(items) == 1
    assert items[0]["ai_generated"] is True
    assert items[0]["abstract"] == "Texto só da IA."
    assert items[0]["has_ementa"] is False
