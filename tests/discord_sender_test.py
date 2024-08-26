from collections import namedtuple

import pytest
from dags.ro_dou_src.notification.discord_sender import DiscordSender, requests
from pytest_mock import MockerFixture

WEBHOOK = "https://some-url.com/xxx"


@pytest.fixture
def mocked_specs():
    Specs = namedtuple(
        "Specs",
        [
            "discord",
            "hide_filters",
            "header_text",
            "footer_text",
            "no_results_found_text",
        ],
    )
    return Specs(
        {"webhook": WEBHOOK},
        False,
        None,
        None,
        "Nenhum dos termos pesquisados foi encontrado nesta consulta.",
    )


def test_send_discord_data(session_mocker: MockerFixture, mocked_specs):
    session_mocker.patch("dags.ro_dou_src.notification.discord_sender.requests.post")

    sender = DiscordSender(mocked_specs)
    sender.send_data({"content": "string"})

    requests.post.assert_called_with(
        WEBHOOK,
        json={
            "content": "string",
            "username": "Querido Prisma (rodou)",
        },
    )


def test_send_text_to_discord(session_mocker: MockerFixture, mocked_specs):
    session_mocker.patch("dags.ro_dou_src.notification.discord_sender.requests.post")

    sender = DiscordSender(mocked_specs)
    sender.send_text("string")

    requests.post.assert_called_with(
        WEBHOOK,
        json={
            "content": "string",
            "username": "Querido Prisma (rodou)",
        },
    )


def test_send_embeds_to_discord(session_mocker: MockerFixture, mocked_specs):
    session_mocker.patch("dags.ro_dou_src.notification.discord_sender.requests.post")
    sender = DiscordSender(mocked_specs)
    items = [
        {
            "title": "some title",
            "abstract": "some abstract",
            "href": "http://some-link.com",
        },
        {
            "title": "another title",
            "abstract": "another abstract",
            "href": "http://another-link.com",
        },
    ]
    sender.send_embeds(items)

    embeds = items
    for item in embeds:
        item["url"] = item.pop("href")
        item["description"] = item.pop("abstract")

    requests.post.assert_called_with(
        WEBHOOK,
        json={
            "embeds": embeds,
            "username": "Querido Prisma (rodou)",
        },
    )


def _send_report(specs):
    search_report = [
        {
            "result": {
                "single_group": {
                    "lei de acesso à informação": {
                        "single_department": [
                            {
                                "abstract": "GOV.BR/CURSO/563REGULAMENTAÇÃO "
                                "DA __LEI DE ACESSO À INFORMAÇÃO__ "
                                "NOS MUNICÍPIOSA LEI FEDERAL Nº "
                                "12REGULAMENTAÇÃO DA LEI Nº 12.527/2011, "
                                "A __LEI DE ACESSO À INFORMAÇÃO__ E, "
                                "EM BREVE, SERÁ INCORPORADO AO CONTEÚDO",
                                "date": "2023-01-31",
                                "href": "https://querido-diario.nyc3.cdn.digitaloceanspaces.com/3509502/2023-01-31/cd3fe0601a5fd9164b48b77bb14b2f0a78962766.pdf",
                                "section": "QD - Edição " "ordinária ",
                                "title": "Campinas/SP",
                            }
                        ],
                    },
                    "lgpd": {
                        "single_department": [
                            {
                                "abstract": "PESSOAISLEI GERAL DE PROTEÇÃO DE "
                                "DADOS PESSOAIS - __LGPD__Nos termos "
                                "dos Arts. 7º, 10º e 11º da Lei nº 13",
                                "date": "2023-01-31",
                                "href": "https://querido-diario.nyc3.cdn.digitaloceanspaces.com/3518800/2023-01-31/958a384e1cc0cdb545a282e9bb55ea9aa74d4700.pdf",
                                "section": "QD - Edição ordinária ",
                                "title": "Guarulhos/SP",
                            },
                            {
                                "abstract": "cumprimento da Lei Geral de Proteção "
                                "de Dados Pessoal (__LGPD__ - Lei nº "
                                "13.709, de 14 de agosto de 2018), "
                                "alcançaLei 13.709/2018 – Lei Geral de "
                                "Proteção de Dados (__LGPD__);VII -  "
                                "atribuir no âmbito da “Segurança da "
                                "Informação”",
                                "date": "2023-01-31",
                                "href": "https://querido-diario.nyc3.cdn.digitaloceanspaces.com/3556206/2023-01-31/2d0f9088530a78c946ada20ec5558f40c5f92900",
                                "section": "QD - Edição ordinária ",
                                "title": "Valinhos/SP",
                            },
                        ],
                    }
                }
            },
            "header": "Test Discord Report",
            "department": None,
        }
    ]
    sender = DiscordSender(specs)
    sender.send(search_report)


def test_send_report_to_discord__texts(session_mocker: MockerFixture, mocked_specs):
    session_mocker.patch(
        "dags.ro_dou_src.notification.discord_sender.DiscordSender.send_text"
    )
    session_mocker.patch(
        "dags.ro_dou_src.notification.discord_sender.DiscordSender.send_embeds"
    )

    _send_report(mocked_specs)

    args_list = [call[0][0] for call in DiscordSender.send_text.call_args_list]

    assert args_list == [
        "**Test Discord Report**",
        "**Resultados para: lei de acesso à informação**",
        "**Resultados para: lgpd**",
    ]


def test_send_report_to_discord__embeds(session_mocker: MockerFixture, mocked_specs):
    session_mocker.patch(
        "dags.ro_dou_src.notification.discord_sender.DiscordSender.send_text"
    )
    session_mocker.patch(
        "dags.ro_dou_src.notification.discord_sender.DiscordSender.send_embeds"
    )

    _send_report(mocked_specs)

    args_list = [call[0][0] for call in DiscordSender.send_embeds.call_args_list]

    assert args_list == [
        [
            {
                "abstract": "GOV.BR/CURSO/563REGULAMENTAÇÃO DA __LEI DE ACESSO À "
                "INFORMAÇÃO__ NOS MUNICÍPIOSA LEI FEDERAL Nº 12REGULAMENTAÇÃO "
                "DA LEI Nº 12.527/2011, A __LEI DE ACESSO À INFORMAÇÃO__ E, EM "
                "BREVE, SERÁ INCORPORADO AO CONTEÚDO",
                "date": "2023-01-31",
                "href": "https://querido-diario.nyc3.cdn.digitaloceanspaces.com/3509502/2023-01-31/cd3fe0601a5fd9164b48b77bb14b2f0a78962766.pdf",
                "section": "QD - Edição ordinária ",
                "title": "Campinas/SP",
            }
        ],
        [
            {
                "abstract": "PESSOAISLEI GERAL DE PROTEÇÃO DE DADOS PESSOAIS - __LGPD__Nos "
                "termos dos Arts. 7º, 10º e 11º da Lei nº 13",
                "date": "2023-01-31",
                "href": "https://querido-diario.nyc3.cdn.digitaloceanspaces.com/3518800/2023-01-31/958a384e1cc0cdb545a282e9bb55ea9aa74d4700.pdf",
                "section": "QD - Edição ordinária ",
                "title": "Guarulhos/SP",
            },
            {
                "abstract": "cumprimento da Lei Geral de Proteção de Dados Pessoal "
                "(__LGPD__ - Lei nº 13.709, de 14 de agosto de 2018), "
                "alcançaLei 13.709/2018 – Lei Geral de Proteção de Dados "
                "(__LGPD__);VII -  atribuir no âmbito da “Segurança da "
                "Informação”",
                "date": "2023-01-31",
                "href": "https://querido-diario.nyc3.cdn.digitaloceanspaces.com/3556206/2023-01-31/2d0f9088530a78c946ada20ec5558f40c5f92900",
                "section": "QD - Edição ordinária ",
                "title": "Valinhos/SP",
            },
        ],
    ]
