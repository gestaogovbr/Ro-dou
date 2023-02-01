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
