## FAQ e problemas frequentes

Nesta seção, você encontrará perguntas e respostas comuns e solução de problemas mais frequentes na utilização do Ro-DOU.

**1. Do que é preciso para instalar o Ro-DOU?** <br>
Resposta: As instruções detalhadas de instalação estão [neste link](https://gestaogovbr.github.io/Ro-dou/como_utilizar/instalacao/).<br>

**2. Como configurar os parâmetros de pesquisa do Ro-DOU?** <br>
Resposta: Os parâmetros devem ser editados no arquivo em formato yml. <br>

**3. Qual a configuração mínima para a instalação do Ro-DOU?** <br>
Resposta: É recomendado 4 Gb de memória RAM e 2 Gb de espaço em disco pelo menos. <br>

**4. Posso rodar o Ro-DOU no meu computador pessoal?** <br>
Resposta: sim. Atendendo às configurações das perguntas acima, em qualquer sistema operacional com suporte ao Docker. <br>

**5. Quais são as fontes de dados do Ro-DOU?** <br>
Resposta: Os dados são obtidos via INLABS, API da Imprensa Nacional e API do Querido Diário. <br>

**6. De que forma o Ro-DOU é capaz de enviar relatórios?** <br>
Resposta: Via e-mail, Slack, Discord. <br>

**7. Preciso pagar pra usar o Ro-DOU?** <br>
Resposta: Não, ele é gratuito. <br>

**8. Posso usar o Ro-DOU para fazer buscas nas edições mais antigas do DOU?** <br>
Resposta: Sim, basta indicar a data desejada no campo "trigger_date". <br>

**9. Como receber atualizações de versão do Ro-DOU?** <br>
Resposta: Sim, basta acompanhar o change log (log de atualizações) disponível [aqui](https://gestaogovbr.github.io/Ro-dou/changelog/changelog/). <br>

**10. Posso utilizar o Ro-dou na minha empresa privada?** <br>
Resposta: Sim. Não são cobrados direitos autorais ou de exclusividade. <br>

**11. Existe um limite de acessos diário para buscas com o Ro-DOU?** <br>
Resposta: Não. Os acessos são ilimitados. <br>

**12. É necessário fazer alguma configuração de fuso horário para o Ro-DOU?** <br>
Resposta: Sim. O padrão é América-São Paulo para o ambiente Airflow que dá sustentação ao Ro-DOU através da variável chamada AIRFLOW__CORE__DEFAULT__TIMEZONE. <br>

**13. Posso usar o Ro-DOU no exterior?** <br>
Resposta: Sim. O Ro-DOU pode ser executado em qualquer lugar desde que tenha acesso à internet. <br>
