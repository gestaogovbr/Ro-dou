## Notificação de erros na execução das DAGs

É importante recordar que o Ro-DOU permite o envio de mensagens via Slack quando ocorre alguma falha na execução da DAG no Apache Airflow. Para usar essa funcionalidade, efetue as seguintes configurações:

1. Criar o app no Slack conforme orientações do vídeo [How to Add Slack Notifications to Your Airflow DAG's with Airflow Notifiers](https://www.youtube.com/watch?v=4yQJWnhKEa4&ab_channel=TheDataGuy).

2. Criar uma conexão no Apache Airflow com a seguinte configuração:

  * `Connection Id` = `slack_notify_rodou_dagrun`
  * `Connection Type` = `Slack API`
  * `Description` = `{"channel": "nome-do-channel-para-mandar-mensagem"}`
  * `Slack API Token` = `obtido no passo 1`
