from datetime import datetime
import pytest
from dags.ro_dou_src.searchers import QDSearcher, _build_query_payload


@pytest.mark.parametrize(
    'result_as_email, expected',
    [
        (True,
         {
            'abstract': '<p>Dados / <span style="font-family: \'rawline\',sans-serif; '
                'background: #FFA;">LGPD</span>, Lei Federal nº 13709, de '
                '14.08.2018.Data de Assinatura: 08.02.2023.Proteção de Dados / '
                '<span style="font-family: \'rawline\',sans-serif; background: '
                '#FFA;">LGPD</span>, Lei </p>',
            'date': '08/02/2023',
            'href': 'https://querido-diario.nyc3.cdn.digitaloceanspaces.com/4106902/2023-02-08/6147a0767244869c788d3f51a5b7c6bd6be3197e',
            'section': 'QD - Edição ordinária ',
            'title': 'Município de Curitiba - PR'
        }),
        (False,
         {
            'abstract': 'Dados / <span style="font-family: \'rawline\',sans-serif; '
                'background: #FFA;">LGPD</span>, Lei Federal nº 13709, de '
                '14.08.2018.Data de Assinatura: 08.02.2023.Proteção de Dados / '
                '<span style="font-family: \'rawline\',sans-serif; background: '
                '#FFA;">LGPD</span>, Lei ',
            'date': '08/02/2023',
            'href': 'https://querido-diario.nyc3.cdn.digitaloceanspaces.com/4106902/2023-02-08/6147a0767244869c788d3f51a5b7c6bd6be3197e',
            'section': 'QD - Edição ordinária ',
            'title': 'Município de Curitiba - PR'}
        ),
    ])
def test_parse_result_qd(result_as_email: bool, expected: str):
    searcher = QDSearcher()
    input = {
        'date': '2023-02-08',
        'edition': '27',
        'excerpts': ['Dados / <span style="font-family: \'rawline\',sans-serif; '
                    'background: #FFA;">LGPD</span>, Lei Federal nº 13709, de '
                    '14.08.2018.\n'
                    'Data de Assinatura: 08.02.2023.\n'
                    'Proteção de Dados / <span style="font-family: '
                    '\'rawline\',sans-serif; background: #FFA;">LGPD</span>, Lei '],
        'is_extra_edition': False,
        'scraped_at': '2023-02-08T21:29:14.191161',
        'state_code': 'PR',
        'territory_id': '4106902',
        'territory_name': 'Curitiba',
        'txt_url': 'https://querido-diario.nyc3.cdn.digitaloceanspaces.com/4106902/2023-02-08/6147a0767244869c788d3f51a5b7c6bd6be3197e.txt',
        'url': 'https://querido-diario.nyc3.cdn.digitaloceanspaces.com/4106902/2023-02-08/6147a0767244869c788d3f51a5b7c6bd6be3197e'
    }
    parsed = searcher.parse_result(input, result_as_email=result_as_email)

    assert parsed == expected


@pytest.mark.parametrize(
        'pre_tags, post_tags',
        [( '<%%>', '</%%>'),
         ( '<%%>', '</%%>')]
)
def test_build_query_payload(pre_tags: str,
                             post_tags: str):
    payload = _build_query_payload(
        search_term='paralelepípedo',
        reference_date=datetime(2023, 2, 9),
    )
    expected = [
        ('size', 100),
        ('excerpt_size', 250),
        ('sort_by', 'descending_date'),
        ('pre_tags', pre_tags),
        ('post_tags', post_tags),
        ('number_of_excerpts', 3),
        ('published_since', '2023-02-09'),
        ('published_until', '2023-02-09'),
        ('querystring', '"paralelepípedo"')
    ]

    assert payload == expected


@pytest.mark.parametrize(
    'territory_id, expected_payload',
    [
        (3300100, [('territory_ids', 3300100)]),
        ([3300100, 3300159], [('territory_ids', 3300100), ('territory_ids', 3300159)]),
    ]
)
def test_search_with_multiple_territory_ids(territory_id, expected_payload):
    #searcher = QDSearcher()
    payload = []

    # Simula a lógica que foi alterada para suportar múltiplos IDs de território
    if isinstance(territory_id, int):
        territory_id = [territory_id]
    for terr_id in territory_id:
        payload.append(('territory_ids', terr_id))

    assert payload == expected_payload