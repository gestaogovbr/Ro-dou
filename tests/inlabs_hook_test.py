import pytest
import pandas as pd
from datetime import datetime

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
                "texto": ["term1 & term2 ! term3", "term4 & term5" ],
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
    "texto_in, texto_out",
    [
        (  # texto_in
            """
            <p class="identifica">Título da Publicação</p>
            <p class="identifica">Título da Publicação 2</p>
            <p>Lorem ipsum dolor sit amet, consectetur adipiscing elit.
            Phasellus venenatis auctor mauris.</p>
            <p class="data">Brasília/DF, 15 de março de 2024.</p>
            <p class="assina">Pessoa 1</p>
            <p class="cargo">Analista</p>
            """,
            # texto_out
            (
                "Título da Publicação Título da Publicação 2 Lorem ipsum dolor sit amet, "
                "consectetur adipiscing elit. Phasellus venenatis auctor mauris. "
                "Brasília/DF, 15 de março de 2024. Pessoa 1 Analista"
            ),
        )
    ],
)
def test_remove_html_tags(inlabs_hook, texto_in, texto_out):
    print(inlabs_hook.TextDictHandler()._remove_html_tags(texto_in))
    assert inlabs_hook.TextDictHandler()._remove_html_tags(texto_in) == texto_out


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
                """(...) cing elit.
            Phasellus venenatis auctor mauris. Integer id neque quis urna
            ultrices iaculis. Donec et enim mauris. Sed vel massa eget est
            viverra finibus a et magna. <%%>Pellentesque</%%> vel elementum
            mauris, id semper tellus. Vivamus convallis lacinia ex sed
            fermentum. Nulla mollis cursus ipsum vel interdum. Mauris
            facilisis posue (...)"""
            ),
        ),
    ],
)
def test_trim_text(inlabs_hook, texto_in, texto_out):
    print(inlabs_hook.TextDictHandler()._trim_text(texto_in))
    assert inlabs_hook.TextDictHandler()._trim_text(texto_in) == texto_out


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
                        "title": "Título da Publicação 1",
                        "href": "http://xxx.gov.br/",
                        "abstract": "(...) <%%>Lorem</%%> ipsum dolor sit amet. (...)",
                        "date": "15/03/2024",
                        "id": 1,
                        "display_date_sortable": None,
                        "hierarchyList": "Texto exemplo art_category",
                    }
                ],
                "Pellentesque": [
                    {
                        "section": "DOU - Seção 1",
                        "title": "Título da Publicação 2",
                        "href": "http://xxx.gov.br/",
                        "abstract": "(...) Dolor sit amet, consectetur adipiscing elit. <%%>Pellentesque</%%>. (...)",
                        "date": "15/03/2024",
                        "id": 2,
                        "display_date_sortable": None,
                        "hierarchyList": "Texto exemplo art_category",
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
                        "title": "Título da Publicação 1",
                        "href": "http://xxx.gov.br/",
                        "abstract": "<%%>Lorem</%%> ipsum dolor sit amet, consectetur adipiscing elit. Phasellus venenatis auctor mauris. Integer id neque quis urna ultrices iaculis. Donec et enim mauris. Sed vel massa eget est viverra finibus a et magna. Pellentesque vel elementum mauris, id semper tellus. Vivamus convallis lacinia ex sed fermentum. Nulla mollis cursus ipsum vel interdum. Mauris facilisis posuere elit. Proin consectetur tincidunt urna. Cras tincidunt nunc vestibulum velit pellentesque facilisis. Aenean sollicitudin ante elit, vitae vehicula nisi congue id. Brasília/DF, 15 de março de 2024. Pessoa 1 Analista <br>",
                        "date": "15/03/2024",
                        "id": 1,
                        "display_date_sortable": None,
                        "hierarchyList": "Texto exemplo art_category",
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
                        "title": "Título da Publicação 1",
                        "href": "http://xxx.gov.br/",
                        "abstract": """Integer id neque quis urna ultrices iaculis.
                        Donec et enim mauris""",
                        "date": "15/03/2024",
                        "id": 1,
                        "display_date_sortable": None,
                        "hierarchyList": "Texto exemplo art_category",
                    }
                ],
            },
            True,
            True,
        ),
    ],
)
def test_transform_search_results(
    inlabs_hook,
    terms,
    df_in,
    dict_out,
    full_text,
    use_summary):

    r = inlabs_hook.TextDictHandler().transform_search_results(
        response=df_in,
        text_terms=terms,
        ignore_signature_match=False,
        full_text=full_text,
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
                        "title": "Título da Publicação",
                        "href": "http://xxx.gov.br/",
                        "abstract": "(...) <%%>Pellentesque</%%> Phasellus venenatis auctor mauris. (...)",
                        "date": "15/03/2024",
                        "id": 2,
                        "display_date_sortable": None,
                        "hierarchyList": "Texto exemplo art_category",
                    }
                ]
            },
        )
    ],
)
def test_ignore_signature(inlabs_hook, terms, df_in, dict_out):
    r = inlabs_hook.TextDictHandler().transform_search_results(
        response=df_in, text_terms=terms, ignore_signature_match=True
    )
    assert r == dict_out
