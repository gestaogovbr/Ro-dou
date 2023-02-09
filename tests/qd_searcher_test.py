import pytest
from dags.ro_dou.searchers import QDSearcher, _build_query_payload


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
            'date': '2023-02-08',
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
            'date': '2023-02-08',
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

