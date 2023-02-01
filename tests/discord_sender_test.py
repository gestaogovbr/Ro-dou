from pytest_mock import MockerFixture

from dags.ro_dou.discord_sender import DiscordSender, requests


def test_send_discord_data(session_mocker: MockerFixture):
    session_mocker.patch('dags.ro_dou.discord_sender.requests.post')

    webhook = 'https://some-url.com/xxx'

    sender = DiscordSender(webhook)
    sender.send_discord_data(
        {
            'content': 'string'
        })

    requests.post.assert_called_with(
        webhook,
        json={
            'content': 'string',
            'username': 'Querido Prisma (rodou)',
        })
