# Changelog

As principais mudanças realizadas no repositório do [Ro-dou](https://github.com/gestaogovbr/Ro-dou) estão documentadas aqui a partir de 25/04/2023.

## [0.6.1] - 2025-08-29

### What's Changed

- Evita retries desnecessários em falhas por `SSLError` em chamadas de rede — aumenta resiliência nas requests (feat/make-bootstrap).
- Parametriza o `Makefile` para permitir builds e execuções mais flexíveis em CI e em ambientes locais.
- Torna o `Dockerfile` mais resiliente a falhas durante o build (melhor abordagem de retry e tolerância a etapas falhas).
- Ajustes operacionais no `docker-compose.yml` para desenvolvimento local: omissão intencional do campo top-level `version:`, fallbacks seguros para variáveis de ambiente e adição do serviço `smtp4dev` no profile `dev`.
- Melhoria no bootstrap do Airflow: flags para execução automática de migrações e criação de usuário admin para facilitar o desenvolvimento local.
- Atualizações na documentação do fork (README) com destaques das especializações ANPD.

## [0.6.0] - 2025-08-15

## What's Changed

- Adicionar suporte a busca sem termos específicos no Ro-DOU by @Heitorh3 in https://github.com/gestaogovbr/Ro-dou/pull/200
- Cria a tabela article_raw automaticamente ao iniciar o container by @Heitorh3 in https://github.com/gestaogovbr/Ro-dou/pull/187
- Adiciona documentação sobre instalação no WSL by @Heitorh3 in https://github.com/gestaogovbr/Ro-dou/pull/195

### 🚀 Outros

- Atualiza exemplos.md by @Ian070508 in https://github.com/gestaogovbr/Ro-dou/pull/181
- Atualizar a versão do Postgres by @Heitorh3 in https://github.com/gestaogovbr/Ro-dou/pull/186
- Atualização e tradução dos textos para o inglês por @Ian070508 in https://github.com/gestaogovbr/Ro-dou/pull/188
- Personaliza o rodapé do e-mail com a logo do Ro-dou by @Heitorh3 in https://github.com/gestaogovbr/Ro-dou/pull/192
- Atualiza email de contato by @edulauer in https://github.com/gestaogovbr/Ro-dou/pull/193
- Remove o título "None" quando a publicação não contém título by @Heitorh3 in https://github.com/gestaogovbr/Ro-dou/pull/196

## New Contributors

- @Ian070508 made their first contribution in https://github.com/gestaogovbr/Ro-dou/pull/181
- @Heitorh3 made their first contribution in https://github.com/gestaogovbr/Ro-dou/pull/186

**Full Changelog**: https://github.com/gestaogovbr/Ro-dou/compare/0.5.0...0.6.0

## [0.5.0] - 2025-03-11

<!-- Release notes generated using configuration in .github/release.yml at main -->

## What's Changed

### 🚀 Outros

- Adiciona novos parâmetros para o QD by @slfabio in https://github.com/gestaogovbr/Ro-dou/pull/172
  **excerpt_size:** Número máximo de caracteres exibidos no trecho onde o termo de busca foi localizado. (Funcionalidade disponível apenas no Querido Diário)
  **number_of_excerpts:** Número máximo de ocorrências do termo de busca em uma mesma edição. (Funcionalidade disponível apenas no Querido Diário)
  **is_exact_search** Permite realizar buscas avançados no Querido Diário quando False
- Update tests-requirements.txt by @gustavosantosio in https://github.com/gestaogovbr/Ro-dou/pull/173

## New Contributors

- @gustavosantosio made their first contribution in https://github.com/gestaogovbr/Ro-dou/pull/173

**Full Changelog**: https://github.com/gestaogovbr/Ro-dou/compare/0.4.0...0.5.0

## [0.4.0] - 2025-03-05

<!-- Release notes generated using configuration in .github/release.yml at main -->

## What's Changed

- Permitir busca no Querido Diário para um grupo de municípios by @slfabio in https://github.com/gestaogovbr/Ro-dou/pull/148
  A partir desta mudança, é permitido informar uma lista de municípios para buscas no Querido Diário.

- Cria novo parâmetro de filtro por tipo de publicação by @edulauer in https://github.com/gestaogovbr/Ro-dou/pull/154
  O parâmetro pubtype permite filtrar publicações tanto no DOU quanto no INLABS com base no tipo (Decreto, Lei, Ata, etc.).

- Melhorias no deployment local by @edulauer in https://github.com/gestaogovbr/Ro-dou/pull/156

### 🚀 Outros

- Update CHANGELOG.md for 0.2.4 by @github-actions in https://github.com/gestaogovbr/Ro-dou/pull/145

## New Contributors

- @slfabio made their first contribution in https://github.com/gestaogovbr/Ro-dou/pull/148

**Full Changelog**: https://github.com/gestaogovbr/Ro-dou/compare/0.3.2...0.4.0

## [0.3.2] - 2025-01-31

<!-- Release notes generated using configuration in .github/release.yml at main -->

## What's Changed

### 🚀 Outros

- reform auto-generated DAG Docs by @salomaolopes in https://github.com/gestaogovbr/Ro-dou/pull/167

**Full Changelog**: https://github.com/gestaogovbr/Ro-dou/compare/0.3.1...0.3.2

## [0.3.1] - 2025-01-16

## What's Changed

- Remove JSON schemas, as it is no longer needed by @augusto-herrmann in https://github.com/gestaogovbr/Ro-dou/pull/159
- Usar validação de data e UI de calendário nos parâmetros das DAGs in https://github.com/gestaogovbr/Ro-dou/pull/162

## [0.3.0] - 2024-11-12

## What's Changed

- Permitir busca no Querido Diário para um grupo de municípios by @slfabio in https://github.com/gestaogovbr/Ro-dou/pull/148
  A partir desta mudança, é permitido informar uma lista de municípios para buscas no Querido Diário.

- Cria novo parâmetro de filtro por tipo de publicação by @edulauer in https://github.com/gestaogovbr/Ro-dou/pull/154
  O parâmetro pubtype permite filtrar publicações tanto no DOU quanto no INLABS com base no tipo (Decreto, Lei, Ata, etc.).

- Melhorias no deployment local by @edulauer in https://github.com/gestaogovbr/Ro-dou/pull/156

### 🚀 Outros

- Update CHANGELOG.md for 0.2.4 by @github-actions in https://github.com/gestaogovbr/Ro-dou/pull/145

## New Contributors

- @slfabio made their first contribution in https://github.com/gestaogovbr/Ro-dou/pull/148

**Full Changelog**: https://github.com/gestaogovbr/Ro-dou/compare/0.2.4...0.2.5

## [0.2.4] - 2024-09-10

<!-- Release notes generated using configuration in .github/release.yml at main -->

## What's Changed

### Hotfix

Corrige resultados incompletos na busca com filtros por unidades [b57b486a2fb692e3e664e764dcc5e2c0f83c9948](https://github.com/gestaogovbr/Ro-dou/commit/b57b486a2fb692e3e664e764dcc5e2c0f83c9948)

**Full Changelog**: https://github.com/gestaogovbr/Ro-dou/compare/0.2.3...0.2.4

## [0.2.3] - 2024-09-04

<!-- Release notes generated using configuration in .github/release.yml at main -->

## What's Changed

### Hotfix

- Ajusta o código para utilizar XCom_pull de múltiplos Tasks IDs no Airflow 2.10.0. by @edulauer in https://github.com/gestaogovbr/Ro-dou/pull/140

### 🚀 Outros

- Ignore markdown files in CI Tests by @augusto-herrmann in https://github.com/gestaogovbr/Ro-dou/pull/141

**Full Changelog**: https://github.com/gestaogovbr/Ro-dou/compare/0.2.2...0.2.3

## [0.2.2] - 2024-09-02

<!-- Release notes generated using configuration in .github/release.yml at main -->

## What's Changed

- Upgrade Airflow to 2.10.0 by @augusto-herrmann in https://github.com/gestaogovbr/Ro-dou/pull/137

### 🚀 Outros

- Cast tags to a list when generating dags by @augusto-herrmann in https://github.com/gestaogovbr/Ro-dou/pull/135

**Full Changelog**: https://github.com/gestaogovbr/Ro-dou/compare/0.2.1...0.2.2

## [0.2.1] - 2024-08-30

<!-- Release notes generated using configuration in .github/release.yml at main -->

## What's Changed

- Criar busca de exemplo para DOU e Querido Diário (modo misto) by @edulauer in https://github.com/gestaogovbr/Ro-dou/pull/132

### 🚀 Outros

- Hotfix by @edulauer in https://github.com/gestaogovbr/Ro-dou/pull/131

**Full Changelog**: https://github.com/gestaogovbr/Ro-dou/compare/0.2.0...0.2.1

## [0.2.0] - 2024-08-29

<!-- Release notes generated using configuration in .github/release.yml at main -->

## What's Changed

- Os resultados agora são agrupados por unidade, quando informada.
- Utilização do Pydantic para validação dos campos do yaml.

### 🚀 Outros

- Agrupar resultados por unidade by @edulauer in https://github.com/gestaogovbr/Ro-dou/pull/122
- Migrate yaml file validation from JSON schema to Pydantic schemas by @augusto-herrmann in https://github.com/gestaogovbr/Ro-dou/pull/118
- Fix logic operators in result_as_html function by @augusto-herrmann in https://github.com/gestaogovbr/Ro-dou/pull/123
- Add syspath for schemas and change dag.owners to string by @edulauer in https://github.com/gestaogovbr/Ro-dou/pull/125
- Alter trigger to run CI Tests on push only to main branch by @augusto-herrmann in https://github.com/gestaogovbr/Ro-dou/pull/127
- Hotfix para correção de variável no módulo de envio de email by @edulauer in https://github.com/gestaogovbr/Ro-dou/pull/128
- Corrige as linhas e colunas na exportação via CSV by @edulauer in https://github.com/gestaogovbr/Ro-dou/pull/129

**Full Changelog**: https://github.com/gestaogovbr/Ro-dou/compare/0.1.5...0.2.0

## [0.1.5] - 2024-08-09

<!-- Release notes generated using configuration in .github/release.yml at main -->

## What's Changed

- Cria parâmetro opcional para uso da ementa (se houver) da publicação ao invés da janela de contexto ou texto completo. by @edulauer in https://github.com/gestaogovbr/Ro-dou/pull/113
- Cria parâmetro para uso de **dataset** no Data-Aware Schedulling. O schedule da DAG agora pode ser definido por três meios: _cron, dataset_ ou _cron + dataset_ <br>
- by @edulauer in https://github.com/gestaogovbr/Ro-dou/pull/115

**Full Changelog**: https://github.com/gestaogovbr/Ro-dou/compare/0.1.4...0.1.5

## [0.1.4] - 2024-07-30

### What's Changed

- Close p tag in watermark by @augusto-herrmann in https://github.com/gestaogovbr/Ro-dou/pull/109

**Full Changelog**: https://github.com/gestaogovbr/Ro-dou/compare/0.1.3...0.1.4

## [0.1.3] - 2024-07-25

- Cria a nova página de documentação do Ro-DOU no Github Pages
- Cria a marca d'agua do Ro-DOU no template do email
- Adiciona quebra de linhas no texto no modo full_text (INLABS)
- Corrige bug quando a paginação de resultados é igual a 2 (DOU)

### What's Changed

- Update README.md by @marcelosinnerworkings in https://github.com/gestaogovbr/Ro-dou/pull/95
- Fix format for Outlook display by @edulauer in https://github.com/gestaogovbr/Ro-dou/pull/96
- Force justify text by @edulauer in https://github.com/gestaogovbr/Ro-dou/pull/97
- Include parameter for dynamic no result text in notification by @edulauer in https://github.com/gestaogovbr/Ro-dou/pull/98
- add dataset trigger scheduler by @vitorbellini in https://github.com/gestaogovbr/Ro-dou/pull/99
- Fix pagination by @edulauer in https://github.com/gestaogovbr/Ro-dou/pull/104
- Keep line breaks in full text mode by @edulauer in https://github.com/gestaogovbr/Ro-dou/pull/105
- Add watermark in email template by @edulauer in https://github.com/gestaogovbr/Ro-dou/pull/108

### New Contributors

- @marcelosinnerworkings made their first contribution in https://github.com/gestaogovbr/Ro-dou/pull/95

**Full Changelog**: https://github.com/gestaogovbr/Ro-dou/compare/0.1.2...0.1.3

## [0.1.2]

- Integração com o portal INLABS, da Imprensa Nacional, permitindo a leitura das edições do DOU pelos arquivos XML
- Remove dependências com o framework FastETL
- Cria filtro de pesquisa por unidade (department)
- Cria opção de exibição de texto completo da publicação
- Cria opção de busca avançada usando operadores lógicos (INLABS)
- Implementa a opção de múltiplos searchs no mesmo YAML
- Cria opção para omitir metadados (hide_filter) no relatório do clipping
- Cria opção para permitir inclusão de cabeçalho e rodapé no corpo do relatório
- Formata o texto para modo justificado

### What's Changed

- Move DOUhook from FastETL to Ro-dou src by @edulauer in https://github.com/gestaogovbr/Ro-dou/pull/66
- Validate yaml by @vitorbellini in https://github.com/gestaogovbr/Ro-dou/pull/75
- Create filter for department by @edulauer in https://github.com/gestaogovbr/Ro-dou/pull/77
- change exact search to consider special characters by @gutaors in https://github.com/gestaogovbr/Ro-dou/pull/80
- Inlabs db by @vitorbellini in https://github.com/gestaogovbr/Ro-dou/pull/81
- add full_text option by @vitorbellini in https://github.com/gestaogovbr/Ro-dou/pull/82
- Implement search with logical operators by @edulauer in https://github.com/gestaogovbr/Ro-dou/pull/85
- Implement subsearchs by @edulauer in https://github.com/gestaogovbr/Ro-dou/pull/87
- Fix select_terms_from_db bug by @edulauer in https://github.com/gestaogovbr/Ro-dou/pull/88
- Create param hide_filter by @edulauer in https://github.com/gestaogovbr/Ro-dou/pull/90
- Hide filters for slack and discord by @edulauer in https://github.com/gestaogovbr/Ro-dou/pull/91
- Add Header and footer text by @edulauer in https://github.com/gestaogovbr/Ro-dou/pull/93
- Justify text in email report by @edulauer in https://github.com/gestaogovbr/Ro-dou/pull/94

### New Contributors

- @gutaors made their first contribution in https://github.com/gestaogovbr/Ro-dou/pull/80

**Full Changelog**: https://github.com/gestaogovbr/Ro-dou/compare/0.1.1...0.1.2

## [0.1.1]

### What's Changed

fix css file access

## [0.1.0] - 2023-08-31

Altera a forma de encontrar os arquivos de configuração das DAGs (`dag_confs/*.yml`).

Antes considerava que a pasta `dag_confs/` estava na mesma raiz que os arquivos do ro-dou em `./src`. Agora o caminho da(s) pasta(s) deve ser informado pela variável de ambiente `RO_DOU__DAG_CONF_DIR` e separado por `:` quando mais de um.

**Exemplo:**

As pastas `/opt/airflow/dags/repo1/dag_confs` e `/opt/airflow/dags/repo2/dag_confs` possuem arquivos de configuração (yaml) para geração das DAGs do rodou. A variável de ambiente `RO_DOU__DAG_CONF_DIR` deve ser atribuída assim:

```shell
RO_DOU__DAG_CONF_DIR=/opt/airflow/dags/repo1/dag_confs:/opt/airflow/dags/repo2/dag_confs
```

Esta alteração permite que os arquivos de configuração das DAGs (`dag_confs/*.yml`) estejam em qualquer pasta da máquina ou container.

### What's Changed

- Change name organization economia to gestao by @salomaolopes in https://github.com/gestaogovbr/Ro-dou/pull/60
- change dag_confs search by @vitorbellini in https://github.com/gestaogovbr/Ro-dou/pull/62

**Full Changelog**: https://github.com/gestaogovbr/Ro-dou/compare/0.0.7...0.1.0

## [0.0.7] 2023-04-27

### What's Changed

- fix workflow docker build publish

## [0.0.6] 2023-04-27

### What's Changed

- fix workflow docker build publish

## [0.0.5] 2023-04-27

### What's Changed

- fix workflow docker build publish

## [0.0.4] 2023-04-27

### What's Changed

- fix workflow docker build publish

## [0.0.3] 2023-04-27

### What's Changed

- fix workflow docker build publish

## [0.0.2] 2023-04-25

### What's Changed

- Conjunto de mudanças para v.1 by @nitaibezerra in https://github.com/gestaogovbr/Ro-dou/pull/4
- Cria resiliência na chamada da API do DOU by @nitaibezerra in https://github.com/gestaogovbr/Ro-dou/pull/5
- Cria opção de pesquisa no Querido Diário by @nitaibezerra in https://github.com/gestaogovbr/Ro-dou/pull/14
- Trigger date horario local by @edulauer in https://github.com/gestaogovbr/Ro-dou/pull/17
- altera template de data do título do email by @salomaolopes in https://github.com/gestaogovbr/Ro-dou/pull/18
- Incluir serviço do selenium no docker-compose.yml by @nitaibezerra in https://github.com/gestaogovbr/Ro-dou/pull/22
- Adiciona tentativas de execução na função search_text_with_retry by @edulauer in https://github.com/gestaogovbr/Ro-dou/pull/23
- Criar parâmetro para enviar email by @salomaolopes in https://github.com/gestaogovbr/Ro-dou/pull/24
- Make tests run in colored output by @augusto-herrmann in https://github.com/gestaogovbr/Ro-dou/pull/25
- Implementa feature de documentação markdown e informações úteis by @augusto-herrmann in https://github.com/gestaogovbr/Ro-dou/pull/31
- Add documentation and separate tests for DAG Docs by @augusto-herrmann in https://github.com/gestaogovbr/Ro-dou/pull/34
- Fix spelling in "links" by @augusto-herrmann in https://github.com/gestaogovbr/Ro-dou/pull/35
- Fix searching terms read from database by @augusto-herrmann in https://github.com/gestaogovbr/Ro-dou/pull/39
- remove selenium from Ro-dou by @vitorbellini in https://github.com/gestaogovbr/Ro-dou/pull/40
- Mount as a volume only the modules used by Ro-DOU by @augusto-herrmann in https://github.com/gestaogovbr/Ro-dou/pull/44
- Upgrade actions/checkout to v3 in CI by @augusto-herrmann in https://github.com/gestaogovbr/Ro-dou/pull/47
- [dou_dag_generator] enables to find ro_dou folder inside airflow dags… by @vitorbellini in https://github.com/gestaogovbr/Ro-dou/pull/49
- Decouple this project from the airflow2-docker image by @nitaibezerra in https://github.com/gestaogovbr/Ro-dou/pull/51
- Bundle src code and plugin into docker image by @nitaibezerra in https://github.com/gestaogovbr/Ro-dou/pull/53
- [WIP] Discord Integration by @nitaibezerra in https://github.com/gestaogovbr/Ro-dou/pull/50
- Workflow to build and publish docker image by @nitaibezerra in https://github.com/gestaogovbr/Ro-dou/pull/54
- update fastetl import by @vitorbellini in https://github.com/gestaogovbr/Ro-dou/pull/56
- Slack integration by @nitaibezerra in https://github.com/gestaogovbr/Ro-dou/pull/58

### New Contributors

- @nitaibezerra made their first contribution in https://github.com/gestaogovbr/Ro-dou/pull/4

**Full Changelog**: https://github.com/gestaogovbr/Ro-dou/commits/0.0.2

## [0.0.1] 2023-04-25

### What's Changed

- Conjunto de mudanças para v.1 by @nitaibezerra in https://github.com/gestaogovbr/Ro-dou/pull/4
- Cria resiliência na chamada da API do DOU by @nitaibezerra in https://github.com/gestaogovbr/Ro-dou/pull/5
- Cria opção de pesquisa no Querido Diário by @nitaibezerra in https://github.com/gestaogovbr/Ro-dou/pull/14
- Trigger date horario local by @edulauer in https://github.com/gestaogovbr/Ro-dou/pull/17
- altera template de data do título do email by @salomaolopes in https://github.com/gestaogovbr/Ro-dou/pull/18
- Incluir serviço do selenium no docker-compose.yml by @nitaibezerra in https://github.com/gestaogovbr/Ro-dou/pull/22
- Adiciona tentativas de execução na função search_text_with_retry by @edulauer in https://github.com/gestaogovbr/Ro-dou/pull/23
- Criar parâmetro para enviar email by @salomaolopes in https://github.com/gestaogovbr/Ro-dou/pull/24
- Make tests run in colored output by @augusto-herrmann in https://github.com/gestaogovbr/Ro-dou/pull/25
- Implementa feature de documentação markdown e informações úteis by @augusto-herrmann in https://github.com/gestaogovbr/Ro-dou/pull/31
- Add documentation and separate tests for DAG Docs by @augusto-herrmann in https://github.com/gestaogovbr/Ro-dou/pull/34
- Fix spelling in "links" by @augusto-herrmann in https://github.com/gestaogovbr/Ro-dou/pull/35
- Fix searching terms read from database by @augusto-herrmann in https://github.com/gestaogovbr/Ro-dou/pull/39
- remove selenium from Ro-dou by @vitorbellini in https://github.com/gestaogovbr/Ro-dou/pull/40
- Mount as a volume only the modules used by Ro-DOU by @augusto-herrmann in https://github.com/gestaogovbr/Ro-dou/pull/44
- Upgrade actions/checkout to v3 in CI by @augusto-herrmann in https://github.com/gestaogovbr/Ro-dou/pull/47
- [dou_dag_generator] enables to find ro_dou folder inside airflow dags… by @vitorbellini in https://github.com/gestaogovbr/Ro-dou/pull/49
- Decouple this project from the airflow2-docker image by @nitaibezerra in https://github.com/gestaogovbr/Ro-dou/pull/51
- Bundle src code and plugin into docker image by @nitaibezerra in https://github.com/gestaogovbr/Ro-dou/pull
