## Exemplos de configuração do arquivo YAML

Neste segmento, você encontrará uma série de exemplos práticos de utilização do Ro-DOU. A leitura dos exemplos ajudará a visualizar de que maneira o Ro-DOU pode ser utilizado.

### Exemplo 1

A configuração a seguir cria uma DAG que realiza a pesquisa **diária** dos
**6 termos listados** e envia o relatório para o **e-mail** fornecido.

```yaml
dag:
  id: pesquisa_dou_termos_interesse_nitai
  description: Pesquisa termos de interesse de Nitai.
  search:
    terms:
      - dados abertos
      - governo aberto
      - engenharia de dados
      - software livre
      - código aberto
      - open source
  report:
    emails:
      - endereco@dominio.com
```

### Exemplo 2

A configuração a seguir realiza a pesquisa diária de **segunda-feira a sexta-feira, 8AM**, apenas na **Seção 1 e na Edição Suplementar** e envia o resultado em **formato CSV**, anexado ao e-mail. O parâmetro `schedule`
aceita valores CRON.

```yaml
dag:
  id: dag_id_deve_ser_unico_em_todo_airflow
  description: DAG exemplo de monitoramento no DOU.
  schedule: 0 8 * * MON-FRI
  search:
    terms:
      - alocação
      - realoca
      - permuta
      - estrutura regimental
      - organização básica
    dou_sections:
      - SECAO_1
      - EDICAO_SUPLEMENTAR
  report:
    emails:
      - dest1@gestao.gov.br
      - dest2@gestao.gov.br
    attach_csv: True
    subject: Assunto do Email
```

Note que aqui são utilizados os parâmetros opcionais `schedule`,
`dou_section` e `attach_csv`.

### Exemplo 3

A configuração a seguir utiliza o parâmetro `from_db_select` em `terms`, que torna dinâmica a parametrização dos termos para pesquisa. Note também a inclusão de `tags` que ajudam na organização e na busca das DAGs no Airflow.

```yaml
dag:
  id: dag_ultra_dinamica
  description: A pesquisa depende do select SQL.
  tags:
    - projeto_a
    - departamento_x
  search:
    terms:
      from_db_select:
        sql: SELECT text FROM schema.tabela;
        conn_id: airflow_conn_id
  report:
    emails:
      - email-destino@gestao.gov.br
    subject: "[String] com caracteres especiais deve estar entre aspas"
```

### Exemplo 4

A configuração a seguir utiliza o parâmetro `from_airflow_variable` em `terms`, que também carrega dinamicamente a lista de termos. Neste caso, há a recuperação a partir de uma **variável do Airflow**. Aqui, também é utilizado o campo `field` para limitar as pesquisas ao campo título das publicações no Diário Oficial da União.

```yaml
dag:
  id: pesquisa_a_lista_na_variavel
  description: É fácil editar a variável na interface do Airflow.
  search:
    terms:
      from_airflow_variable: nome_da_variavel_no_airflow
    field: TITULO
  report:
    emails:
      - email-destino@gestao.gov.br
    skip_null: False
```
Caso não encontre nenhum resultado, será enviado um e-mail informando que
nenhum termo foi encontrado.


### Exemplo 5

A configuração a seguir produz uma DAG que executa apenas **uma vez por mês**, no dia 1 às 8 AM, como pode ser visto no `schedule`. Simultaneamente, a pesquisa no Diário Oficial da União é realizada nos diários oficiais do **último mês** inteiro, através do uso do parâmetro `date`. Aqui, também é utilizado o parâmetro `is_exact_search`
com valor `False` para utilizar uma pesquisa aproximada.

Apesar do fato de que o termo buscado "paralelpip**i**do" contenha um erro ortográfico, a busca retorna os resultados corretos. [Veja!](https://www.in.gov.br/consulta/-/buscar/dou?q=ddm__text__21040__texto_pt_BR-paralelepipido&s=todos&exactDate=ano&sortType=0)

```yaml
dag:
  id: relatorio_mensal_do_dou
  description: Envia um numero menor de emails.
  schedule: 0 8 1 * *
  search:
    terms:
      - paralelpipido
    date: MES
    is_exact_search: False
  report:
    emails:
      - email-destino@gestao.gov.br
```

### Exemplo 6

A configuração a seguir produz uma DAG que pesquisa no Querido Diário pelos termos "pandemia", "dados pessoais" e "prefeitura", buscando apenas os resultados do Diário Oficial de Belo Horizonte. Para conhecer o Querido Diário, acesse
[https://queridodiario.ok.org.br/](https://queridodiario.ok.org.br/).

```yaml
dag:
  id: dou_qd_example
  description: DAG de teste
  search:
    sources:
    - QD
    territory_id: 3106200 # Belo Horizonte
    terms:
    - pandemia
    - dados pessoais
    - prefeitura
  report:
    emails:
      - destination@gestao.gov.br
    attach_csv: True
    subject: "Teste do Ro-dou"
```

### Exemplo 7

A configuração a seguir produz uma DAG exatamente igual ao exemplo básico, mas adiciona uma descrição longa do que a DAG faz, usando o parâmetro
`doc_md`. Essa descrição pode conter formatação markdown, incluindo
títulos, listas, links etc.

Além disso, acrescenta também uma referência ao nome do arquivo que
gerou a DAG, bem como os seus parâmetros.

```yaml
dag:
  id: markdown_docs_example
  description: DAG com documentação em markdown
  search:
    terms:
    - dados abertos
    - governo aberto
    - lei de acesso à informação
  report:
    emails:
      - destination@gestao.gov.br
    subject: "Teste do Ro-dou"
  doc_md: >-
    ## Ola!

    Esta é uma DAG de exemplo com documentação em markdown. Esta
    descrição é opcional e pode ser definida no parâmetro `doc_md`.

      * Ah, aqui você também pode usar *markdown* para
      * escrever listas, por exemplo,
      * ou colocar [links](graph)!
```

Para ver essa documentação, basta clicar o botão "DAG Docs" em qualquer
tela de visualização da DAG no Airflow.

![Botão "DAG Docs". Captura de tela da documentação de DAG no Airflow.](https://github.com/gestaogovbr/Ro-dou/blob/main/docs/img/exemplo-dag-doc_md.png?raw=true)

### Exemplo 8
Esta configuração envia as notificações para canais Discord. É necessário ter
permissões de administrador no Discord para gerar o Webhook:

```yaml
dag:
  id: discord_example
  description: Envia notificações para canal Discord
  search:
    terms:
    - manifestação cultural
    - expressão cultural
    - política cultural
  report:
    report:
    discord:
      webhook: https://discord.com/api/webhooks/105220xxxxxx811250/Q-XsfdnoHtudTQ-8A6zzzzznitai-vi0bGLE7xxxxxxxxxxxxxxxxxxxmx94R3oZ1h0ngl1
```

### Exemplo 9
Esta configuração envia as notificações para canais Slack. É necessário ter
permissões de administrador no Slack para gerar o Webhook:

```yaml
dag:
  id: slack_example
  description: Envia notificações para canal Slack
  search:
    terms:
    - manifestação cultural
    - expressão cultural
    - política cultural
  report:
    report:
    slack:
      webhook: https://hooks.slack.com/services/XXXXXXXX/XXXXNFDXXX/n6QXXXXrPwxQ71ZXXXXXT9
```

### Exemplo 10
Esta configuração filtra os resultados por órgão/unidade selecionados.
Por enquanto disponível apenas para as pesquisas no DOU.

```yaml
dag:
  id: department_example
  description: DAG de teste (filtro por departamento)
  search:
    terms:
      - dados abertos
    department:
      - Ministério da Gestão e da Inovação em Serviços Públicos
      - Ministério da Defesa
  report:
    emails:
      - destination@gestao.gov.br
    subject: "Teste do Ro-dou"
```

### Exemplo 11
Esta configuração permite múltiplas buscas utilizando o mesmo arquivo.
O Ro-dou permite numa mesma busca juntar resultados do DOU e Querido Diário.

```yaml
dag:
  id: multiple_searchs_example
  description: DAG de teste com múltiplas buscas
  search:
    - header: "Pesquisa no DOU"
      sources:
        - DOU
      terms:
        - dados abertos
        - governo aberto
        - lei de acesso à informação
      force_rematch: On
      ignore_signature_match: On
    - header: "Pesquisa no QD"
      sources:
        - QD
      terms:
        - dados abertos
        - governo aberto
        - lei de acesso à informação
      force_rematch: On
      ignore_signature_match: On
    - header: "Pesquisa no DOU e QD (misto)"
      sources:
        - DOU
        - QD
      terms:
        - dados abertos
        - governo aberto
        - lei de acesso à informação
      force_rematch: On
      ignore_signature_match: On
  report:
    emails:
      - destination@gestao.gov.br
    subject: "Teste do Ro-dou"
```

### Exemplo 12
Esta configuração filtra os resultados por tipos de publicações selecionadas.
Disponível para as pesquisas no DOU e INLABS.

```yaml
dag:
  id: pubtype_example
  description: DAG de teste (filtro por tipo de publicação)
  search:
    sources:
      - DOU
    terms:
      - programa
    pubtype:
      - Ato
      - Portaria
      - Edital
      - Extrato
      - Ratificação
      - Resolução
      - Retificação
      - Protocolo
  report:
    emails:
      - destination@gestao.gov.br
    subject: "Teste do Ro-dou"
```