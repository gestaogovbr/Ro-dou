## FAQ e problemas frequentes

Nesta seção, você encontrará perguntas e respostas comuns e solução de problemas mais frequentes na utilização do Ro-DOU.

1. **Do que é preciso para instalar o Ro-DOU?** <br>
As instruções detalhadas de instalação estão [neste link](https://gestaogovbr.github.io/Ro-dou/como_utilizar/instalacao/).

1. **Como configurar os parâmetros de pesquisa do Ro-DOU?** <br>
Os parâmetros devem ser editados no arquivo em formato yml. 

1. **Qual a configuração mínima para a instalação do Ro-DOU?** <br>
É recomendado 4 Gb de memória RAM e 2 Gb de espaço em disco pelo menos.

1. **Posso rodar o Ro-DOU no meu computador pessoal?** <br>
Sim. O Ro-DOU pode ser instalado em qualquer sistema operacional com suporte ao Docker.

1. **Quais são as fontes de dados do Ro-DOU?** <br>
 Os dados são obtidos via INLABS, API da Imprensa Nacional e API do Querido Diário.

1. **De que forma o Ro-DOU é capaz de enviar relatórios?** <br>
Via e-mail, Slack, Discord.

1. **Preciso pagar pra usar o Ro-DOU?** <br>
Não, ele é gratuito.

1. **Posso usar o Ro-DOU para fazer buscas nas edições mais antigas do DOU?** <br>
Sim, basta indicar a data desejada no campo "trigger_date" ao disparar manualmente a DAG.

1. **Como receber atualizações de versão do Ro-DOU?** <br>
Sim, basta acompanhar o change log (log de atualizações) disponível [aqui](https://gestaogovbr.github.io/Ro-dou/changelog/changelog/).

1. **Posso utilizar o Ro-dou em meu órgão?** <br>
Sim. Confira as instruções [aqui](https://gestaogovbr.github.io/Ro-dou/como_utilizar/usuarios/).

1. **Posso utilizar o Ro-dou na minha empresa privada?** <br>
Sim. Não são cobrados direitos autorais ou de exclusividade.

1. **Existe um limite de acessos diário para buscas com o Ro-DOU?** <br>
Não. Os acessos são ilimitados.

1. **É necessário fazer alguma configuração de fuso horário para o Ro-DOU?** <br>
Sim. O padrão é América-São Paulo para o ambiente Airflow que dá sustentação ao Ro-DOU através da variável de ambiente chamada AIRFLOW__CORE__DEFAULT__TIMEZONE.

1. **Posso usar o Ro-DOU no exterior?** <br>
Sim. O Ro-DOU pode ser executado em qualquer lugar desde que tenha acesso à internet.
