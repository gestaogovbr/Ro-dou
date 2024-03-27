import pytest


@pytest.mark.parametrize(
    "text, keys, matches",
    [
        (
            "Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
            ["lorem", "sit", "not_find"],
            ["lorem", "sit"]
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
    "date_in, date_out",
    [
        ("2024-03-07", "07/03/2024"),
    ],
)
def test_format_date(inlabs_hook, date_in, date_out):
    assert inlabs_hook.TextDictHandler()._format_date(date_in) == date_out


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
        (   # texto_in
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
            ("Título da Publicação Título da Publicação 2 Lorem ipsum dolor sit amet, "
            "consectetur adipiscing elit. Phasellus venenatis auctor mauris. "
            "Brasília/DF, 15 de março de 2024. Pessoa 1 Analista")
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
        (   # texto_in
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
            ("""(...) cing elit.
            Phasellus venenatis auctor mauris. Integer id neque quis urna
            ultrices iaculis. Donec et enim mauris. Sed vel massa eget est
            viverra finibus a et magna. <%%>Pellentesque</%%> vel elementum
            mauris, id semper tellus. Vivamus convallis lacinia ex sed
            fermentum. Nulla mollis cursus ipsum vel interdum. Mauris
            facilisis posue (...)""")
        ),
    ],
)
def test_trim_text(inlabs_hook, texto_in, texto_out):
    print(inlabs_hook.TextDictHandler()._trim_text(texto_in))
    assert inlabs_hook.TextDictHandler()._trim_text(texto_in) == texto_out


@pytest.mark.parametrize(
    "terms, list_in, dict_out",
    [
        (
            # terms
            ["Lorem", "Pellentesque"],
            # list_in
            [
                {
                    "title": "Título da Publicação",
                    "href": "http://xxx.gov.br/",
                    "date": "2024-03-15",
                    "section": "DO1",
                    "abstract": "Lorem ipsum dolor sit amet.",
                },
                {
                    "title": "Título da Publicação",
                    "href": "http://xxx.gov.br/",
                    "date": "2024-03-15",
                    "section": "DO1",
                    "abstract": "Pellentesque vel elementum mauris.",
                },
                {
                    "title": "Título da Publicação",
                    "href": "http://xxx.gov.br/",
                    "date": "2024-03-15",
                    "section": "DO1",
                    "abstract": "Dolor sit amet, lórem consectetur adipiscing elit.",
                },
            ],
            # dict_out
            {
                "Lorem": [
                    {
                        "title": "Título da Publicação",
                        "href": "http://xxx.gov.br/",
                        "date": "2024-03-15",
                        "section": "DO1",
                        "abstract": "Lorem ipsum dolor sit amet.",
                    },
                    {
                        "title": "Título da Publicação",
                        "href": "http://xxx.gov.br/",
                        "date": "2024-03-15",
                        "section": "DO1",
                        "abstract": "Dolor sit amet, lórem consectetur adipiscing elit.",
                    },
                ],
                "Pellentesque": [
                    {
                        "title": "Título da Publicação",
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
def test_update_nested_dict(inlabs_hook, terms, list_in, dict_out):
    all_results = {}
    for item in list_in:
        for term in terms:
            if inlabs_hook.TextDictHandler()._normalize(
                term.upper()
            ) in inlabs_hook.TextDictHandler()._normalize(item["abstract"].upper()):
                all_results = inlabs_hook.TextDictHandler()._update_nested_dict(
                    all_results, term, item
                )

    assert all_results == dict_out


@pytest.mark.parametrize(
    "terms, list_in, dict_out",
    [
        (
            ["Pellentesque", "Lorem"],
            [
                {
                    "art_category": "Texto exemplo art_category",
                    "art_type": "Publicação xxx",
                    "article_id": 1,
                    "assina": "Pessoa 1",
                    "data": "Brasília/DF, 15 de março de 2024.",
                    "ementa": "None",
                    "identifica": "Título da Publicação",
                    "name": "15.03.2024 bsb DOU xxx",
                    "pdf_page": "http://xxx.gov.br/",
                    "pub_date": "2024-03-15",
                    "pub_name": "DO1",
                    "sub_titulo": "None",
                    "texto": "Lorem ipsum dolor sit amet.",
                    "titulo": "None",
                },
                {
                    "art_category": "Texto exemplo art_category",
                    "art_type": "Publicação xxx",
                    "article_id": 2,
                    "assina": "Pessoa 2",
                    "data": "Brasília/DF, 15 de março de 2024.",
                    "ementa": "None",
                    "identifica": "Título da Publicação",
                    "name": "15.03.2024 bsb DOU xxx",
                    "pdf_page": "http://xxx.gov.br/",
                    "pub_date": "2024-03-15",
                    "pub_name": "DO1",
                    "sub_titulo": "None",
                    "texto": "Dolor sit amet, consectetur adipiscing elit. Pellentesque.",
                    "titulo": "None",
                },
            ],
            {
                "Lorem": [
                    {
                        "section": "DOU - Seção 1",
                        "title": "Título da Publicação",
                        "href": "http://xxx.gov.br/",
                        "abstract": "(...) <%%>Lorem</%%> ipsum dolor sit amet. (...)",
                        "date": "15/03/2024",
                        "id": 1,
                        "display_date_sortable": None,
                        "hierarchyList": None,
                    }
                ],
                "Pellentesque": [
                    {
                        "section": "DOU - Seção 1",
                        "title": "Título da Publicação",
                        "href": "http://xxx.gov.br/",
                        "abstract": "(...) Dolor sit amet, consectetur adipiscing elit. <%%>Pellentesque</%%>. (...)",
                        "date": "15/03/2024",
                        "id": 2,
                        "display_date_sortable": None,
                        "hierarchyList": None,
                    }
                ],
            },
        )
    ],
)
def test_transform_search_results(inlabs_hook, terms, list_in, dict_out):
    r = inlabs_hook.TextDictHandler().transform_search_results(
        response=list_in, text_terms=terms, ignore_signature_match=False
    )
    assert r == dict_out


@pytest.mark.parametrize(
    "terms, list_in, dict_out",
    [
        (   # terms
            ["Pellentesque", "Pessoa 1"],
            # list_in
            [
                {
                    "art_category": "Texto exemplo art_category",
                    "art_type": "Publicação xxx",
                    "article_id": 1,
                    "assina": "Pessoa 1",
                    "data": "Brasília/DF, 15 de março de 2024.",
                    "ementa": "None",
                    "identifica": "Título da Publicação",
                    "name": "15.03.2024 bsb DOU xxx",
                    "pdf_page": "http://xxx.gov.br/",
                    "pub_date": "2024-03-15",
                    "pub_name": "DO1",
                    "sub_titulo": "None",
                    "texto": "Pessoa 1 ipsum dolor sit amet.",
                    "titulo": "None",
                },
                {
                    "art_category": "Texto exemplo art_category",
                    "art_type": "Publicação xxx",
                    "article_id": 2,
                    "assina": "Pessoa 2",
                    "data": "Brasília/DF, 15 de março de 2024.",
                    "ementa": "None",
                    "identifica": "Título da Publicação",
                    "name": "15.03.2024 bsb DOU xxx",
                    "pdf_page": "http://xxx.gov.br/",
                    "pub_date": "2024-03-15",
                    "pub_name": "DO1",
                    "sub_titulo": "None",
                    "texto": "Pellentesque Phasellus venenatis auctor mauris.",
                    "titulo": "None",
                },
            ],
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
                        "hierarchyList": None,
                    }
                ]
            },
        )
    ],
)
def test_ignore_signature(inlabs_hook, terms, list_in, dict_out):
    r = inlabs_hook.TextDictHandler().transform_search_results(
        response=list_in, text_terms=terms, ignore_signature_match=True
    )
    assert r == dict_out
