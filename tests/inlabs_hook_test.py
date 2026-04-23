import pytest
import pandas as pd
import numpy as np
from datetime import datetime
import importlib.util
from datetime import datetime
from unittest.mock import MagicMock, patch
from airflow.models import Variable
from ai.provider import AIProvider
from schemas import AIConfig, AISearchConfig

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

_MIN_AI_SEARCH_CONFIG = AISearchConfig(
    use_ai_summary=False,
)

@pytest.mark.parametrize(
    "text_terms_in, text_terms_out",
    [
        (["lorem & ( ipsum | dolor)"], ["lorem", "ipsum", "dolor"]),
    ],
)
def test_filter_text_terms(inlabs_hook, text_terms_in, text_terms_out):
    assert inlabs_hook._filter_text_terms(text_terms_in) == text_terms_out


@pytest.mark.parametrize(
    "data_in, query_out",
    [
        (
            {
                "texto": ["term1", "term2"],
                "pubname": ["DO1"],
                "pubdate": ["2024-04-01", "2024-04-02"],
            },
            "SELECT * FROM dou_inlabs.article_raw WHERE (pubdate BETWEEN '2024-04-01' AND '2024-04-02') AND (dou_inlabs.unaccent(texto) ~* dou_inlabs.unaccent('\\yterm1\\y') OR dou_inlabs.unaccent(texto) ~* dou_inlabs.unaccent('\\yterm2\\y')) AND (dou_inlabs.unaccent(pubname) ~* dou_inlabs.unaccent('\\yDO1\\y'))",
        ),
    ],
)
def test_generate_sql(inlabs_hook, data_in, query_out):
    assert inlabs_hook._generate_sql(data_in)["select"] == query_out


@pytest.mark.parametrize(
    "data_in, query_out",
    [
        (
            {
                "texto": ["term1 & term2 ! term3", "term4 & term5"],
                "pubname": ["DO1"],
                "pubdate": ["2024-04-01", "2024-04-02"],
            },
            "SELECT * FROM dou_inlabs.article_raw WHERE (pubdate BETWEEN '2024-04-01' AND '2024-04-02') AND ((dou_inlabs.unaccent(texto) ~* dou_inlabs.unaccent('\\yterm1\\y') AND dou_inlabs.unaccent(texto) ~* dou_inlabs.unaccent('\\yterm2\\y') AND dou_inlabs.unaccent(texto) !~* dou_inlabs.unaccent('\\yterm3\\y')) OR (dou_inlabs.unaccent(texto) ~* dou_inlabs.unaccent('\\yterm4\\y') AND dou_inlabs.unaccent(texto) ~* dou_inlabs.unaccent('\\yterm5\\y'))) AND (dou_inlabs.unaccent(pubname) ~* dou_inlabs.unaccent('\\yDO1\\y'))",
        ),
    ],
)
def test_generate_sql_with_search_operators(inlabs_hook, data_in, query_out):
    assert inlabs_hook._generate_sql(data_in)["select"] == query_out


@pytest.mark.parametrize(
    "data_in, query_out",
    [
        (
            {
                "pubname": ["DO1"],
                "arttype": ["Portaria", "Resolução"],
                "pubdate": ["2024-04-01", "2024-04-02"],
            },
            "SELECT * FROM dou_inlabs.article_raw WHERE (pubdate BETWEEN '2024-04-01' AND '2024-04-02') AND (dou_inlabs.unaccent(pubname) ~* dou_inlabs.unaccent('\\yDO1\\y')) AND (dou_inlabs.unaccent(arttype) ~* dou_inlabs.unaccent('\\yPortaria\\y') OR dou_inlabs.unaccent(arttype) ~* dou_inlabs.unaccent('\\yResolução\\y'))",
        ),
    ],
)
def test_generate_sql_no_terms(inlabs_hook, data_in, query_out):
    assert inlabs_hook._generate_sql(data_in)["select"] == query_out


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


@pytest.mark.parametrize(
    "text, keys, matches",
    [
        (
            "Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
            ["lorem", "sit", "not_find"],
            "lorem, sit",
        ),
    ],
)
def test_find_matches(inlabs_hook, text, keys, matches):
    assert inlabs_hook.TextDictHandler()._find_matches(text, keys) == matches


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
            (
                """(...) . Sed ut perspiciatis
            unde omnis iste natus error sit voluptatem accusantium doloremque laudantium,
            totam rem aperiam, eaque ipsa Lorem ipsum dolor sit amet, consectetur adipiscing elit.
            Phasellus venenatis auctor mauris. Integer id neque quis urna
            ultrices iaculis. Donec et enim mauris. Sed vel massa eget est
            viverra finibus a et magna. <%%>Pellentesque</%%> vel elementum
            mauris, id semper tellus. Vivamus convallis lacinia ex sed
            fermentum. Nulla mollis cursus ipsum vel interdum. Mauris
            facilisis posuere elit. Proin consectetur tincidunt urna.
            Cras tincidunt nunc vestibulum velit pellentesque facilisis.
            Aenean sollicitudin ante elit, vitae vehicula nisi congue id. (...)"""
            ),
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
            (
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
            adipisci velit, sed quia non numquam eius modi tempora (...)"""
            ),
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
            (
                """(...) . Sed ut perspiciatis
            unde omnis iste natus error sit voluptatem accusantium doloremque laudantium,
            totam rem aperiam, eaque ipsa Lorem ipsum dolor sit amet, consectetur adipiscing elit.
            Phasellus venenatis auctor mauris. Integer id neque quis urna
            ultrices iaculis. Donec et enim mauris. Sed vel massa eget est
            viverra finibus a et magna. <%%>Pellentesque</%%> vel elementum
            mauris, id semper tellus. Vivamus convallis lacinia ex sed
            fermentum. Nulla mollis cursus ipsum vel interdum. Mauris
            facilisis posuere elit. Proin consectetur tincidunt urna.
            Cras tincidunt nunc vestibulum velit pellentesque facilisis.
            Aenean sollicitudin ante elit, vitae vehicula nisi congue id. (...)"""
            ),
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


@pytest.mark.parametrize(
    "terms, df_in, dict_out, full_text, use_summary",
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
                        "abstract": "<%%><%%>Lorem</%%></%%> ipsum dolor sit amet.",
                        "date": "15/03/2024",
                        "id": 1,
                        "display_date_sortable": None,
                        "hierarchyList": "Texto exemplo art_category",
                        "ai_generated": False,
                    }
                ],
                "Pellentesque": [
                    {
                        "section": "DOU - Seção 1",
                        "title": "TÍTULO DA PUBLICAÇÃO 2",
                        "href": "http://xxx.gov.br/",
                        "abstract": "Dolor sit amet, consectetur adipiscing elit. <%%><%%>Pellentesque</%%></%%>.",
                        "date": "15/03/2024",
                        "id": 2,
                        "display_date_sortable": None,
                        "hierarchyList": "Texto exemplo art_category",
                        "ai_generated": False,
                    }
                ],
            },
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
                            "<%%><%%>Lorem</%%></%%> ipsum dolor sit amet, consectetur adipiscing elit.\n"
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
                    }
                ],
            },
            True,
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
                    }
                ],
            },
            True,
            True,
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
                        "abstract": "<p><%%><%%>Lorem</%%></%%> ipsum dolor sit amet.</p>",
                        "date": "15/03/2024",
                        "id": 1,
                        "display_date_sortable": None,
                        "hierarchyList": "Texto exemplo art_category",
                        "ai_generated": False,
                    }
                ],
            },
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
                    }
                ],
            },
            False,
            False,
        ),
    ],
)
def test_transform_search_results(
    inlabs_hook, terms, df_in, dict_out, full_text, use_summary
):

    r = inlabs_hook.TextDictHandler().transform_search_results(
        ai_config=_MIN_AI_CONFIG,
        response=df_in,
        text_terms=terms,
        ignore_signature_match=False,
        ai_search_config=_MIN_AI_SEARCH_CONFIG,
        full_text=full_text,
        text_length=400,
        use_summary=use_summary,
    )
    assert r == dict_out


@pytest.mark.parametrize(
    "terms, df_in, dict_out",
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
                        "abstract": "<%%><%%>Pellentesque</%%></%%> Phasellus venenatis auctor mauris.",
                        "date": "15/03/2024",
                        "id": 2,
                        "display_date_sortable": None,
                        "hierarchyList": "Texto exemplo art_category",
                        "ai_generated": False,
                    }
                ]
            },
        )
    ],
)
def test_ignore_signature(inlabs_hook, terms, df_in, dict_out):
    r = inlabs_hook.TextDictHandler().transform_search_results(
        ai_config=_MIN_AI_CONFIG,
        ai_search_config=_MIN_AI_SEARCH_CONFIG,
        response=df_in,
        text_terms=terms,
        ignore_signature_match=True,
    )
    assert r == dict_out


@pytest.mark.parametrize(
    "data_in, query_out",
    [
        (
            {
                "texto": ["term1", "term2"],
                "pubname": ["DO1"],
                "pubdate": ["2024-04-01", "2024-04-02"],
                "artcategory": ["Ministério da Defesa"],
                "artcategory_ignore": ["Ministério da Defesa/Comando da Marinha"],
            },
            r"SELECT * FROM dou_inlabs.article_raw WHERE (pubdate BETWEEN '2024-04-01' AND '2024-04-02') AND (dou_inlabs.unaccent(texto) ~* dou_inlabs.unaccent('\yterm1\y') OR dou_inlabs.unaccent(texto) ~* dou_inlabs.unaccent('\yterm2\y')) AND (dou_inlabs.unaccent(pubname) ~* dou_inlabs.unaccent('\yDO1\y')) AND (dou_inlabs.unaccent(artcategory) ~* dou_inlabs.unaccent('\yMinistério da Defesa\y')) AND (dou_inlabs.unaccent(artcategory) !~* dou_inlabs.unaccent('^Ministério da Defesa/Comando da Marinha'))",
        ),
    ],
)
def test_generate_sql_with_department(inlabs_hook, data_in, query_out):
    assert inlabs_hook._generate_sql(data_in)["select"] == query_out


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
        (
            "ab <table><tr><td>x</td></tr></table> cd",
            4,
            " <table><tr><td>x</td></tr></table> cd",
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


def test_transform_search_results_ai_respects_pub_limit(inlabs_hook):
    df = pd.DataFrame(
        [
            _sample_row(id=1, texto="Lorem " * 30),
            _sample_row(id=2, identifica="Título 2", texto="Lorem " * 30),
            _sample_row(id=3, identifica="Título 3", texto="Lorem " * 30),
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
            )
    assert mock_run.call_count == 3


def test_transform_search_results_ai_system_prompt_uses_matches(inlabs_hook):
    df = pd.DataFrame([_sample_row()])
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
            )
    mock_run.assert_called_once()
    kwargs = mock_run.call_args.kwargs
    assert kwargs["system_prompt"] == "Enfatize Lorem na análise"
    assert kwargs["provider"] == AIProvider.openai
    assert kwargs["model"] == "gpt-4o-mini"


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
        with patch(f"{_INLABS_HOOK}.AIRunner.run", return_value="Resumo IA.") as mock_run:
            inlabs_hook.TextDictHandler().transform_search_results(
                ai_config=_MIN_AI_CONFIG,
                ai_search_config=ai_search_config,
                response=df,
                text_terms=["Lorem"],
                ignore_signature_match=False,
                use_summary=True,
            )
    assert mock_run.call_count == 1
    kwargs = mock_run.call_args.kwargs
    assert "Lorem" in kwargs["input_text"]


def test_transform_search_results_ai_sets_ai_generated_flag(inlabs_hook):
    df = pd.DataFrame([_sample_row()])
    ai_search_config = AISearchConfig(
        use_ai_summary=True,
    )
    with patch(f"{_INLABS_HOOK}.Variable.get", return_value="sk-fake"):
        with patch(f"{_INLABS_HOOK}.AIRunner.run", return_value="Texto só da IA."):
            out = inlabs_hook.TextDictHandler().transform_search_results(
                ai_config=_MIN_AI_CONFIG,
                ai_search_config=ai_search_config,
                response=df,
                text_terms=["Lorem"],
                ignore_signature_match=False,
            )
    items = [item for group in out.values() for item in group]
    assert len(items) == 1
    assert items[0]["ai_generated"] is True
    assert items[0]["abstract"] == "Texto só da IA."