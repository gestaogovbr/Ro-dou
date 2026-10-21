import logging
from datetime import datetime
from unittest import mock
import pytest
import requests
from dags.ro_dou_src.searchers import QDSearcher, _build_query_payload

SEARCHERS = "dags.ro_dou_src.searchers"


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
        is_exact_search=True,
        reference_date=datetime(2023, 2, 9),
        territory_id=None,
    )
    expected = [
        ('size', 100),
        ('excerpt_size', 250),
        ('sort_by', 'relevance'),
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
        (
            None, 
            [
                ('size', 100),
                ('excerpt_size', 250),
                ('sort_by', 'relevance'),
                ('pre_tags',  "<%%>"),
                ('post_tags',  "</%%>"),
                ('number_of_excerpts', 3),
                ('published_since', '2023-02-09'),
                ('published_until', '2023-02-09'),
                ('querystring', '"paralelepípedo"')
            ]
        ),
        (
            3303302, 
            [
                ('size', 1),
                ('excerpt_size', 250),
                ('sort_by', 'relevance'),
                ('pre_tags',  "<%%>"),
                ('post_tags',  "</%%>"),
                ('number_of_excerpts', 3),
                ('published_since', '2023-02-09'),
                ('published_until', '2023-02-09'),
                ('querystring', '"paralelepípedo"'),
                ('territory_ids', 3303302)
            ]
        ),
        (
            [3303302, 3303303], 
            [
                ('size', 2),
                ('excerpt_size', 250),
                ('sort_by', 'relevance'),
                ('pre_tags',  "<%%>"),
                ('post_tags',  "</%%>"),
                ('number_of_excerpts', 3),
                ('published_since', '2023-02-09'),
                ('published_until', '2023-02-09'),
                ('querystring', '"paralelepípedo"'),
                ('territory_ids', 3303302),
                ('territory_ids', 3303303)
            ]
        ),
    ]
)
def test_build_query_payload_territory_id_and_size(territory_id, expected_payload):
    payload = _build_query_payload(
        search_term='paralelepípedo',
        is_exact_search=True,
        reference_date=datetime(2023, 2, 9),
        territory_id=territory_id
    )
    
    assert payload == expected_payload

@pytest.mark.parametrize(
    'excerpt_size, number_of_excerpts, expected_payload',
    [
        (
            500, 
            5, 
            [
                ('size', 100),
                ('excerpt_size', 500),
                ('sort_by', 'relevance'),
                ('pre_tags',  "<%%>"),
                ('post_tags',  "</%%>"),
                ('number_of_excerpts', 5),
                ('published_since', '2023-02-09'),
                ('published_until', '2023-02-09'),
                ('querystring', '"paralelepípedo"')
            ]
        )
    ]
)
def test_build_query_payload_excerpt_params(excerpt_size, number_of_excerpts, expected_payload):
    payload = _build_query_payload(
        search_term='paralelepípedo',
        is_exact_search=True,
        reference_date=datetime(2023, 2, 9),
        territory_id=None,
        excerpt_size=excerpt_size,
        number_of_excerpts=number_of_excerpts
    )
    
    assert payload == expected_payload

@pytest.mark.parametrize(
    'is_exact_search, expected_search_term',
    [
        (True, '"paralelepípedo"'),
        (False, 'paralelepípedo')
    ]
)
def test_search_with_is_exact_search(is_exact_search, expected_search_term):
    
    payload = _build_query_payload(
        search_term='paralelepípedo',
        is_exact_search=is_exact_search,
        reference_date=datetime(2023, 2, 9),
        territory_id=None,
        excerpt_size=250,
        number_of_excerpts=3
    )
    querystring = payload[-1][1]
    
    assert querystring == expected_search_term

@mock.patch(f"{SEARCHERS}.time.sleep")
@mock.patch(f"{SEARCHERS}.requests.get")
def test_get_with_retry_recupera_apos_falha_temporaria(mock_get, mock_sleep):
    mock_get.side_effect = [mock.Mock(status_code=520), mock.Mock(status_code=200)]

    assert QDSearcher()._get_with_retry([], "termo").status_code == 200
    assert mock_get.call_count == 2
    mock_sleep.assert_called_once_with(2)


@mock.patch(f"{SEARCHERS}.time.sleep")
@mock.patch(f"{SEARCHERS}.requests.get")
def test_get_with_retry_falha_persistente_esgota_tentativas(mock_get, mock_sleep):
    mock_get.return_value = mock.Mock(status_code=520)

    with pytest.raises(requests.HTTPError, match="HTTP 520"):
        QDSearcher()._get_with_retry([], "termo")
    assert mock_get.call_count == QDSearcher.MAX_ATTEMPTS
    assert [c.args[0] for c in mock_sleep.call_args_list] == [2, 4]


@pytest.mark.parametrize(
    "exc",
    [
        requests.Timeout(),
        requests.ConnectionError(),
        requests.exceptions.ChunkedEncodingError(),
        requests.exceptions.ContentDecodingError(),
    ],
)
@mock.patch(f"{SEARCHERS}.time.sleep")
@mock.patch(f"{SEARCHERS}.requests.get")
def test_get_with_retry_repete_falha_de_rede(mock_get, mock_sleep, exc):
    mock_get.side_effect = [exc, mock.Mock(status_code=200)]

    assert QDSearcher()._get_with_retry([], "termo").status_code == 200
    assert mock_get.call_count == 2


@mock.patch(f"{SEARCHERS}.time.sleep")
@mock.patch(f"{SEARCHERS}.requests.get")
def test_get_with_retry_timeout_persistente_propaga_erro(mock_get, mock_sleep):
    mock_get.side_effect = requests.Timeout()

    with pytest.raises(requests.Timeout):
        QDSearcher()._get_with_retry([], "termo")
    assert mock_get.call_count == QDSearcher.MAX_ATTEMPTS


@mock.patch(f"{SEARCHERS}.time.sleep")
@mock.patch(f"{SEARCHERS}.requests.get")
def test_get_with_retry_nao_repete_erro_do_cliente(mock_get, mock_sleep):
    mock_get.return_value = mock.Mock(status_code=400)

    assert QDSearcher()._get_with_retry([], "termo").status_code == 400
    assert mock_get.call_count == 1
    mock_sleep.assert_not_called()


@mock.patch(f"{SEARCHERS}.requests.get")
def test_get_with_retry_usa_url_e_timeout(mock_get):
    mock_get.return_value = mock.Mock(status_code=200)
    payload = [("querystring", "termo")]

    QDSearcher()._get_with_retry(payload, "termo")

    mock_get.assert_called_once_with(
        "https://api.queridodiario.org.br/gazettes",
        params=payload,
        timeout=QDSearcher.REQUEST_TIMEOUT,
    )


@pytest.mark.parametrize(
    "exc",
    [
        requests.exceptions.SSLError("certificado inválido"),
        requests.TooManyRedirects("redirecionamentos demais"),
    ],
)
@mock.patch(f"{SEARCHERS}.time.sleep")
@mock.patch(f"{SEARCHERS}.requests.get")
def test_get_with_retry_nao_repete_erro_permanente(mock_get, mock_sleep, exc, caplog):
    mock_get.side_effect = exc

    with caplog.at_level(logging.ERROR), pytest.raises(type(exc)):
        QDSearcher()._get_with_retry([], "licitação")

    assert mock_get.call_count == 1
    mock_sleep.assert_not_called()
    assert "licitação" in caplog.text
    assert str(exc) in caplog.text


@mock.patch(f"{SEARCHERS}.requests.get")
def test_get_with_retry_sem_tentativas_configuradas_falha(mock_get):
    searcher = QDSearcher()
    searcher.MAX_ATTEMPTS = 0

    with pytest.raises(ValueError, match="MAX_ATTEMPTS"):
        searcher._get_with_retry([], "termo")
    mock_get.assert_not_called()


@mock.patch(f"{SEARCHERS}.time.sleep")
@mock.patch(f"{SEARCHERS}.requests.get")
def test_get_with_retry_registra_termo_e_causa(mock_get, mock_sleep, caplog):
    mock_get.side_effect = requests.Timeout("lento demais")

    with caplog.at_level(logging.WARNING), pytest.raises(requests.Timeout):
        QDSearcher()._get_with_retry([], "licitação")

    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    errors = [r for r in caplog.records if r.levelno == logging.ERROR]
    assert len(warnings) == QDSearcher.MAX_ATTEMPTS - 1
    assert len(errors) == 1
    for record in warnings + errors:
        assert "licitação" in record.getMessage()
        assert "lento demais" in record.getMessage()


def _response(status_code: int, content: bytes) -> requests.Response:
    response = requests.Response()
    response.status_code = status_code
    response._content = content
    response.url = QDSearcher.API_BASE_URL
    return response


def _search_term(searcher: QDSearcher, search_term: str = "licitação") -> list:
    return searcher._search_term(
        territory_id=None,
        search_term=search_term,
        is_exact_search=False,
        reference_date=datetime(2026, 10, 20),
        excerpt_size=250,
        number_of_excerpts=3,
    )


@mock.patch(f"{SEARCHERS}.requests.get")
def test_search_term_status_de_erro_nao_vira_busca_vazia(mock_get, caplog):
    mock_get.return_value = _response(404, b"<html>Not Found</html>")

    with caplog.at_level(logging.ERROR), pytest.raises(requests.HTTPError):
        _search_term(QDSearcher())

    assert mock_get.call_count == 1
    assert "licitação" in caplog.text


@pytest.mark.parametrize(
    "content",
    [
        b"<html>manutencao</html>",
        b"[]",
        b'{"total_gazettes": 0}',
        b'{"total_gazettes": 0, "gazettes": null}',
    ],
)
@mock.patch(f"{SEARCHERS}.requests.get")
def test_search_term_json_invalido_nao_vira_busca_vazia(mock_get, content, caplog):
    mock_get.return_value = _response(200, content)

    with caplog.at_level(logging.ERROR), pytest.raises(ValueError, match="licitação"):
        _search_term(QDSearcher())

    assert "licitação" in caplog.text


@mock.patch(f"{SEARCHERS}.requests.get")
def test_search_term_sem_publicacoes_retorna_lista_vazia(mock_get):
    mock_get.return_value = _response(200, b'{"total_gazettes": 0, "gazettes": []}')

    assert _search_term(QDSearcher()) == []
