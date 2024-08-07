## FAQ e problemas frequentes

Nesta seção, você encontrará perguntas e respostas comuns e solução de problemas mais frequentes na utilização do Ro-DOU.

1. Do que é preciso para instalar o Ro-DOU?
Resposta: As instruções detalhadas de instalação estão [neste link](https://gestaogovbr.github.io/Ro-dou/como_utilizar/instalacao/).

1. Como configurar os parâmetros de pesquisa do Ro-DOU?
Resposta: Os parâmetros devem ser editados no arquivo em formato yml.

1. Qual a configuração mínima para a instalação do Ro-DOU?
Resposta: É recomendado 4 Gb de memória RAM e 2 Gb de espaço em disco pelo menos.

3. Posso rodar o Ro-DOU no meu computador pessoal? 
Resposta: sim. Atendendo às configurações das perguntas acima, em qualquer sistema operacional com suporte ao Docker.

2. Quais são as fontes de dados do Ro-DOU?
Resposta: As fontes de dados são obtidas via INLABS, API da Imprensa Nacional e API do Querido Diário.

3. De que forma o Ro-DOU é capaz de enviar relatórios?
Resposta: Via e-mail, Slack, Discord.

6. Preciso pagar pra usar o Ro-DOU?
Resposta: Não, ele é gratuito.

7. Posso usar o ro-dou para fazer buscas nas edições mais antigas do DOU?
Resposta: Sim, basta indicar a data desejada no campo "trigger_date".

8. Como receber atualizações de versão do Ro-DOU?
Resposta: Sim, basta acompanhar o change log (log de atualizações) disponível [aqui](https://gestaogovbr.github.io/Ro-dou/changelog/changelog/).

9. Posso utilizar o Ro-dou na minha empresa privada?
Resposta: Sim. Não são cobrados direitos autorais ou de exclusividade.

10. Existe um limite de acessos diário para buscas com o Ro-DOU?
Resposta: Não. Os acessos são ilimitados.

11. É necessário fazer alguma configuração de fuso horário para o Ro-DOU?
Resposta: Sim. O padrão é América-São Paulo para o ambiente Airflow que dá sustentação ao Ro-DOU através da variável chamada AIRFLOW__CORE__DEFAULT__TIMEZONE.

12. Posso usar o Ro-DOU no exterior?
Resposta: Sim. O Ro-DOU pode ser executado em qualquer lugar desde que tenha acesso à internet.
