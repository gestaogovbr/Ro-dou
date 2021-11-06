# Ro-dou

O Ro-dou é uma ferramenta para gerar dinamicamente DAGs no
[Apache Airflow](https://airflow.apache.org/) que fazem *clipping* do Diário
Oficial da União ([DOU](https://www.gov.br/imprensanacional/pt-br)) à partir de
arquivos **YAML**. Receba no email todas as publicações que contenham as
**palavras chaves** que você definir.

# Recursos

- Frequência **diária**, **semanal** ou **mensal**
- Relatório em `.CSV`
- Busca dinâmica das palavras chaves no **DB** ou de uma **Variável**
- Pesquisa em **Seção** específica


# Exemplos de Uso

### Exemplo 1
A configuração a seguir cria uma DAG que realiza a pesquisa **diária** dos
**6 termos** e envia o relatório para o **email** fornecido.

```yaml {6-10,13}
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
      - nitaibezerra@protonmail.com
```

### Exemplo 2
Esta configuração realiza a pesquisa diária de **segunda a sexta-feira 8AM UTC**,
apenas na **Seção 1 e na Edição Suplementar** e envia o resultado em
**formato CSV** anexado juntamente ao email. O parâmetro `schedule_interval`
aceita valores CRON.

```yaml {4,13-14,19}
dag:
  id: dag_id_deve_ser_unico_em_todo_airflow
  description: DAG exemplo de monitoramento no DOU.
  schedule_interval: 0 8 * * MON-FRI
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
      - dest1@economia.gov.br
      - dest2@economia.gov.br
    attach_csv: True
    subject: Assunto do Email
```
Note que aqui são utilizados os parâmetros opcionais `schedule_interval`,
`dou_section` e `attach_csv`.

### Exemplo 3
Neste caso é utilizado o parâmetro `from_db_select` em `terms` que torna
dinâmica a parametrização dos termos para pesquisa. Note também a inclusão de
`tags` que ajudam na organização e busca das DAGs no Airflow.

```yaml {4-6,9-11}
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
      - email-destino@economia.gov.br
    subject: "[String] com caracteres especiais deve estar entre aspas"
```

### Exemplo 4
Nesta configuração é utilizado o parâmetro `from_airflow_variable` em `terms`
que também carrega dinamicamente a lista de termos, neste caso recuperando de
uma **variável do Airflow**. Aqui também é utilizado o campo `field` para
limitar as pesquisas ao campo título das publicações no DOU.

```yaml {6,7}
dag:
  id: pesquisa_a_lista_na_variavel
  description: É fácil editar a variável na interface do Airflow.
  search:
    terms:
      from_airflow_variable: nome_da_variavel_no_airflow
    field: TITULO
  report:
    emails:
      - email-destino@economia.gov.br
```

### Exemplo 5
Esta configuração produz uma DAG que executa apenas **uma vez por mês**, no dia
1 às 8AM, como pode ser visto no `schedule_interval`. Ao passo que a pesquisa
no DOU é realizada nos diários oficiais do **último mês** inteiro, através do
uso do parâmetro `date`. Aqui também é utilizado o parâmetro `is_exact_search`
com valor `False` para utilizar pesquisa aproximada. Apesar de o termo buscado
"paralelepip**i**do" conter um erro de ortográfico, a busca retorna os
resultados corretos. [Veja!](https://www.in.gov.br/consulta/-/buscar/dou?q=ddm__text__21040__texto_pt_BR-paralelepipido&s=todos&exactDate=ano&sortType=0)

```yaml {4,8,9}
dag:
  id: relatorio_mensal_do_dou
  description: Envia um numero menor de emails.
  schedule_interval: 0 8 1 * *
  search:
    terms:
      - paralelpipido
    date: MES
    is_exact_search: False
  report:
    emails:
      - email-destino@economia.gov.br
```

## Compreendendo um pouco mais a engenhoca

Todos os parâmetros disponíveis para pesquisa foram criados a partir da API da
Imprensa Nacional que por sua vez é utilizada pelo buscador oficial do DOU em
https://www.in.gov.br/consulta/. Ou seja, o Ro-dou consegue automatizar todo,
ou quase todo, tipo de pesquisa que pode ser feita no site do DOU. A imagem
abaixo é o painel de pesquisa avançada do site:

![Captura de tela do painel de pesquisa avançada no site do DOU.](docs/img/parametros-pesquisa-avancada-dou.png)
# Parâmetros de pesquisa disponíveis

Por padrão, caso omitido, o valor  do parâmetro `dou_section` é **TODOS**. Ou
seja, a pesquisa é feita em todas as seções do DOU. Este campo aceita mais de
uma opção.
* `dou_sections`:
  * SECAO_1
  * SECAO_2
  * SECAO_3
  * EDICAO_EXTRA
  * EDICAO_SUPLEMENTAR
  * TODOS


* `date`:
  * DIA
  * SEMAN
  * MES
  * ANO


* `field`:
  * TUDO
  * TITULO
  * CONTEUDO
