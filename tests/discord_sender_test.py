from pytest_mock import MockerFixture

from dags.ro_dou.discord_sender import DiscordSender, requests

WEBHOOK = 'https://some-url.com/xxx'

def test_send_discord_data(session_mocker: MockerFixture):
    session_mocker.patch('dags.ro_dou.discord_sender.requests.post')

    sender = DiscordSender(WEBHOOK)
    sender.send_discord_data(
        {
            'content': 'string'
        })

    requests.post.assert_called_with(
        WEBHOOK,
        json={
            'content': 'string',
            'username': 'Querido Prisma (rodou)',
        })


def test_send_text_to_discord(session_mocker: MockerFixture):
    session_mocker.patch('dags.ro_dou.discord_sender.requests.post')

    sender = DiscordSender(WEBHOOK)
    sender.send_text_to_discord('string')

    requests.post.assert_called_with(
        WEBHOOK,
        json={
            'content': 'string',
            'username': 'Querido Prisma (rodou)',
        })


def test_send_embeds_to_discord(session_mocker: MockerFixture):
    session_mocker.patch('dags.ro_dou.discord_sender.requests.post')

    sender = DiscordSender(WEBHOOK)
    items = [
        {
            'title': 'some title',
            'abstract': 'some abstract',
            'href': 'http://some-link.com',
        },
        {
            'title': 'another title',
            'abstract': 'another abstract',
            'href': 'http://another-link.com',
        },
    ]
    sender.send_embeds_to_discord(items)

    requests.post.assert_called_with(
        WEBHOOK,
        json={
            'embeds': [
                {
                    'title': 'some title',
                    'description': 'some abstract',
                    'url': 'http://some-link.com',
                },
                {
                    'title': 'another title',
                    'description': 'another abstract',
                    'url': 'http://another-link.com',
                },
            ],
            'username': 'Querido Prisma (rodou)',
        })


def _send_report():
    search_report = {
        'single_group': {
            'lei de acesso à informação': [
                {
                    'abstract': 'GOV.BR/CURSO/563REGULAMENTAÇÃO '
                                'DA __LEI DE ACESSO À INFORMAÇÃO__ '
                                'NOS MUNICÍPIOSA LEI FEDERAL Nº '
                                '12REGULAMENTAÇÃO DA LEI Nº 12.527/2011, '
                                'A __LEI DE ACESSO À INFORMAÇÃO__ E, '
                                'EM BREVE, SERÁ INCORPORADO AO CONTEÚDO',
                    'date': '2023-01-31',
                    'href': 'https://querido-diario.nyc3.cdn.digitaloceanspaces.com/3509502/2023-01-31/cd3fe0601a5fd9164b48b77bb14b2f0a78962766.pdf',
                    'section': 'QD - Edição '
                                'ordinária ',
                    'title': 'Campinas/SP'
                }
            ],
            'lgpd': [
                {
                    'abstract': 'PESSOAISLEI GERAL DE PROTEÇÃO DE '
                                'DADOS PESSOAIS - __LGPD__Nos termos '
                                'dos Arts. 7º, 10º e 11º da Lei nº 13',
                    'date': '2023-01-31',
                    'href': 'https://querido-diario.nyc3.cdn.digitaloceanspaces.com/3518800/2023-01-31/958a384e1cc0cdb545a282e9bb55ea9aa74d4700.pdf',
                    'section': 'QD - Edição ordinária ',
                    'title': 'Guarulhos/SP'
                },
                {
                    'abstract': 'cumprimento da Lei Geral de Proteção '
                                'de Dados Pessoal (__LGPD__ - Lei nº '
                                '13.709, de 14 de agosto de 2018), '
                                'alcançaLei 13.709/2018 – Lei Geral de '
                                'Proteção de Dados (__LGPD__);VII -  '
                                'atribuir no âmbito da “Segurança da '
                                'Informação”',
                    'date': '2023-01-31',
                    'href': 'https://querido-diario.nyc3.cdn.digitaloceanspaces.com/3556206/2023-01-31/2d0f9088530a78c946ada20ec5558f40c5f92900',
                    'section': 'QD - Edição ordinária ',
                    'title': 'Valinhos/SP'
                }
            ]
        }
    }

    sender = DiscordSender(WEBHOOK)
    sender._send_discord(search_report)


def test_send_report_to_discord__texts(session_mocker: MockerFixture):
    session_mocker.patch(
        'dags.ro_dou.discord_sender.DiscordSender.send_text_to_discord')
    session_mocker.patch(
        'dags.ro_dou.discord_sender.DiscordSender.send_embeds_to_discord')

    _send_report()

    args_list =[
        call.args[0]
        for call in DiscordSender.send_text_to_discord.call_args_list
    ]

    assert args_list == [
        '**Resultados para: lei de acesso à informação**',
        '**Resultados para: lgpd**'
    ]


def test_send_report_to_discord__embeds(session_mocker: MockerFixture):
    session_mocker.patch(
        'dags.ro_dou.discord_sender.DiscordSender.send_text_to_discord')
    session_mocker.patch(
        'dags.ro_dou.discord_sender.DiscordSender.send_embeds_to_discord')

    _send_report()

    args_list =[
        call.args[0]
        for call in DiscordSender.send_embeds_to_discord.call_args_list
    ]

    assert args_list == [
        [
            {
                'abstract': 'GOV.BR/CURSO/563REGULAMENTAÇÃO DA __LEI DE ACESSO À '
                    'INFORMAÇÃO__ NOS MUNICÍPIOSA LEI FEDERAL Nº 12REGULAMENTAÇÃO '
                    'DA LEI Nº 12.527/2011, A __LEI DE ACESSO À INFORMAÇÃO__ E, EM '
                    'BREVE, SERÁ INCORPORADO AO CONTEÚDO',
                'date': '2023-01-31',
                'href': 'https://querido-diario.nyc3.cdn.digitaloceanspaces.com/3509502/2023-01-31/cd3fe0601a5fd9164b48b77bb14b2f0a78962766.pdf',
                'section': 'QD - Edição ordinária ',
                'title': 'Campinas/SP'
            }
        ],
        [
            {
                'abstract': 'PESSOAISLEI GERAL DE PROTEÇÃO DE DADOS PESSOAIS - __LGPD__Nos '
                    'termos dos Arts. 7º, 10º e 11º da Lei nº 13',
                'date': '2023-01-31',
                'href': 'https://querido-diario.nyc3.cdn.digitaloceanspaces.com/3518800/2023-01-31/958a384e1cc0cdb545a282e9bb55ea9aa74d4700.pdf',
                'section': 'QD - Edição ordinária ',
                'title': 'Guarulhos/SP'
            },
            {
                'abstract': 'cumprimento da Lei Geral de Proteção de Dados Pessoal '
                    '(__LGPD__ - Lei nº 13.709, de 14 de agosto de 2018), '
                    'alcançaLei 13.709/2018 – Lei Geral de Proteção de Dados '
                    '(__LGPD__);VII -  atribuir no âmbito da “Segurança da '
                    'Informação”',
                'date': '2023-01-31',
                'href': 'https://querido-diario.nyc3.cdn.digitaloceanspaces.com/3556206/2023-01-31/2d0f9088530a78c946ada20ec5558f40c5f92900',
                'section': 'QD - Edição ordinária ',
                'title': 'Valinhos/SP'
            }
        ]
    ]