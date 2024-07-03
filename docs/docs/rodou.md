# O que é Ro-DOU?

Nesta seção, você encontrará as seguintes informações sobre o Ro-DOU:

* Definição
* Arquitetura

## Definição

Conforme dito na página inicial, o Ro-DOU é uma ferramenta que efetua um *clipping* do Diário
Oficial da União ([D.O.U.](https://www.gov.br/imprensanacional/pt-br)) e dos Diários Oficiais de municípios, por meio do [Querido Diário](https://queridodiario.ok.org.br/). O Ro-DOU permite o recebimento de notificações (via e-mail, Slack, Discord ou outros) de todas as publicações que contenham as **palavras-chaves** que você definir.

O Ro-DOU gera dinamicamente grafos acíclicos dirigidos (DAGs) no [Apache Airflow](https://airflow.apache.org/). Uma DAG nada mais é que um fluxo de tarefas executadas em sequência ou de maneira paralela, a partir de um código Python. Para entender com mais detalhes técnicos como uma DAG do Airflow funciona, [clique aqui](https://airflow.apache.org/docs/apache-airflow/1.10.9/concepts.html).

Nos arquivos YAML, é possível configurar os detalhes dos termos de pesquisa desejado (as palavras-chaves) e os contatos (e.g. endereços de e-mail) para recebimento dos resultados da pesquisa.

## Arquitetura

A maneira como os diferentes componentes do Ro-DOU se relacionam pode ser sintetizada no diagrama abaixo. Para ampliar a imagem, [clique aqui](https://github.com/gestaogovbr/Ro-dou/blob/main/docs/img/rodou_arquitetura.png?raw=true).

![Diagrama de arquitetura do Ro-DOU](https://github.com/gestaogovbr/Ro-dou/blob/main/docs/img/rodou_arquitetura.png?raw=true)




