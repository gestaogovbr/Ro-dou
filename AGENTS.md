# Guia de agentes do Ro-DOU

Este arquivo orienta agentes que atuam neste repositório. Ele se aplica a todo o projeto a partir da raiz. Instruções mais específicas, caso sejam adicionadas em subdiretórios, prevalecem somente dentro do respectivo escopo.

## Visão do projeto

O Ro-DOU é uma aplicação de clipping de diários oficiais executada sobre Apache Airflow. Arquivos YAML descrevem buscas, agenda e destinos; modelos Pydantic validam essas configurações; o gerador cria DAGs dinamicamente; os buscadores consultam DOU, INLABS, Querido Diário e DOE-SP; e os resultados podem ser enviados por e-mail, Slack ou Discord. Há suporte opcional a resumos por IA e a OpenSearch para buscas do INLABS.

O ambiente local oficial usa Docker Compose com Airflow 3, PostgreSQL, OpenSearch e smtp4dev. A implantação também possui chart Helm. A documentação pública é construída com MkDocs.

## Mapa do repositório

- `src/`: núcleo da aplicação.
  - `dou_dag_generator.py`: montagem dinâmica das DAGs e encadeamento de buscas e notificações.
  - `schemas.py` e `parsers.py`: contrato e validação dos YAMLs.
  - `searchers.py` e `hooks/`: integrações e regras das fontes de dados.
  - `notification/`: formatação e entrega dos relatórios.
  - `ai/`: configuração, provedores e geração opcional de resumos.
  - `utils/`: regras auxiliares compartilhadas.
- `dag_confs/`: configurações de uso; exemplos e casos de teste ficam em `dag_confs/examples_and_tests/`. Mudanças no contrato YAML devem manter esses exemplos válidos.
- `dag_load_inlabs/`: DAGs, utilitários e SQL da carga de publicações do INLABS.
- `tests/`: testes unitários, de integração, carregamento de DAG e execução ponta a ponta.
- `tools/gerador_cli.py`: assistente interativo para gerar YAML.
- `docs/docs/`: fontes Markdown do site; a navegação fica em `docs/mkdocs.yml`.
- `helm/ro-dou/`: chart e manifestos Kubernetes.
- `Dockerfile`, `docker-compose.yml` e `Makefile`: imagem e ambiente local/CI.

Não trate artefatos locais como fonte do produto. Em particular, ignore caches (`__pycache__`, `.pytest_cache`, `.mypy_cache`, `.ruff_cache`), dados e logs em `mnt/`, builds de documentação e relatórios locais de linters.

## Fluxo de trabalho comum

1. Leia o código, testes e documentação diretamente relacionados à solicitação antes de editar.
2. Verifique `git status --short`. A árvore pode conter trabalho não relacionado de outros agentes ou do usuário; não o reverta, formate nem inclua por acidente.
3. Delimite os arquivos sob sua responsabilidade e coordene sobreposição com os demais agentes.
4. Faça a menor mudança coesa. Preserve compatibilidade dos YAMLs e dos IDs/contratos do Airflow, salvo quando uma quebra tiver sido explicitamente aprovada.
5. Adicione ou ajuste testes de regressão próximos ao comportamento alterado.
6. Execute primeiro os testes focados e depois a suíte aplicável. Registre comandos, resultado e qualquer teste não executado.
7. Atualize documentação e exemplos quando mudar configuração, comportamento observável, instalação ou operação.
8. Revise o diff final e confirme que ele contém apenas mudanças intencionais.

Não crie commits, branches, tags, releases nem publique imagens ou documentação sem solicitação explícita. Quando commits forem pedidos, use os prefixos adotados pelo projeto: `feat:`, `fix:`, `docs:`, `chore:`, `refactor:` ou `test:`.

## Comandos do projeto

O caminho validado pela CI é o ambiente Docker:

```bash
make run
make tests
make down
```

- `make run` constrói e sobe o ambiente, cria conexões/variáveis locais e ativa a DAG de carga do INLABS. Pode baixar imagens, alterar contêineres e levar vários minutos; use-o somente quando esse nível de integração for necessário.
- `make tests` executa `pytest -vvv` dentro do contêiner `airflow-api-server`; o ambiente precisa estar ativo.
- Para um teste focado, use, com o ambiente ativo:

```bash
docker exec airflow-api-server sh -c "cd /opt/airflow/tests && pytest -q caminho_do_teste.py::nome_do_teste"
```

- `make gerar-yml` executa o gerador interativo e também requer o contêiner ativo.
- `make create-opensearch-variable` e `make create-azure-openai-variables` alteram a configuração do Airflow local; não os rode como simples validação.
- Para conferir a documentação sem publicá-la:

```bash
docker compose -f docs/docker-compose.yml run --rm mkdocs mkdocs build
```

- Para alterações no chart, valide quando as ferramentas estiverem disponíveis:

```bash
helm lint helm/ro-dou
helm template ro-dou helm/ro-dou
```

Não execute `mkdocs gh-deploy`, push de imagens ou comandos de implantação como parte de uma validação local.

## Regras por papel

### Agente de novas funcionalidades

- Trace o fluxo completo `YAML -> parsers.py -> schemas.py -> dou_dag_generator.py -> hook/searcher/sender`. Um novo campo YAML normalmente exige validação, propagação, teste e documentação em todas as etapas aplicáveis.
- Reutilize as abstrações existentes: `BaseSearcher` para fontes, `ISender`/`Notifier` para canais e a camada `ai/` para provedores de IA.
- Preserve o formato de resultados `grupo -> termo -> departamento -> itens`; templates, merge e notificadores dependem desse contrato. Valide explicitamente os valores de `sources` e não amplie as ramificações especiais de `merge_results` sem casos de teste que demonstrem a necessidade.
- Para um novo canal de notificação, prefira a integração via Apprise; crie uma implementação dedicada somente quando o canal exigir comportamento que a biblioteca não suporte.
- Preserve os imports e caminhos usados dentro do Airflow (`/opt/airflow/dags/ro_dou_src`) e considere a serialização de argumentos entre tasks.
- Para integrações externas, defina timeout, tratamento de erro, retries compatíveis com Airflow e testes com mocks; não dependa de rede real nos testes unitários.
- Mantenha exemplos em `dag_confs/examples_and_tests/` sincronizados com o contrato e confirme o carregamento das DAGs.

### Agente de segurança

- Faça revisão orientada a risco e reporte achados com arquivo/linha, cenário de exploração, impacto, evidência e correção proposta. Diferencie vulnerabilidade confirmada de melhoria defensiva.
- Priorize fronteiras externas: URLs e payloads das buscas, webhooks de notificação, conteúdo HTML/Markdown, credenciais do INLABS, consultas configuráveis, prompts/respostas de IA, arquivos YAML e APIs do Airflow.
- Verifique SSRF, injeção SQL/comandos/templates, XSS em relatórios, traversal, desserialização insegura, vazamento em logs, ausência de timeout/TLS e permissões excessivas.
- Nunca use `shell=True` com caminhos ou valores oriundos de `Variable`, YAML, XCom ou outra entrada. Prefira APIs Python ou argumentos de subprocesso sem shell e valide caminhos contra uma raiz permitida.
- Toda extração ZIP deve impedir Zip Slip (caminhos absolutos, `..`, links e escape do diretório de destino) e impor limites de quantidade e tamanho descompactado para evitar bombas ZIP.
- Mantenha o pickling de XCom desabilitado em produção; a opção presente no Compose só pode ser tratada como compatibilidade legada/local e não deve ser propagada ao Helm ou a novos ambientes.
- Não use `|safe` em conteúdo externo sem sanitização prévia com `nh3`. Valide também esquema, host e finalidade de URLs antes de buscar conteúdo ou montar links/webhooks.
- Considere `docker-compose.yml` uma configuração local de desenvolvimento: credenciais e chaves padrão nunca devem ser promovidas a produção. Em Helm, use Secrets/referências externas e evite valores reais em `values.yaml` ou manifests.
- Não teste exploração contra serviços externos ou ambientes compartilhados. Use fixtures, mocks e o ambiente local autorizado.
- Nunca exponha o valor de `.env`, tokens, senhas, chaves, conexões do Airflow ou segredos Kubernetes em saída, patch, exemplo ou relatório. Se encontrar segredo real, informe apenas o local e o tipo e recomende revogação/rotação.

### Agente de revisão de código novo

- Acione este agente depois que uma implementação alterar código Python, DAGs, schemas, templates, dependências, Docker ou Helm e antes de considerar a tarefa concluída. A revisão deve ser independente da implementação.
- Trabalhe em modo somente leitura por padrão. Não corrija o código durante a revisão, salvo quando o usuário pedir explicitamente; entregue achados para o agente implementador tratar.
- Comece pelo pedido original, `git status --short` e diff da mudança. Revise apenas o código novo ou afetado e o contexto mínimo necessário, sem atribuir ao autor alterações preexistentes do worktree.
- Procure defeitos funcionais, regressões, casos-limite, contratos quebrados, erros de tipagem, concorrência, idempotência de tasks, retries que duplicam efeitos, uso excessivo de memória/rede e falhas de observabilidade.
- Confirme que schemas, exemplos YAML, geração/carregamento de DAGs e canais de notificação permanecem compatíveis quando essas áreas forem tocadas.
- Avalie se os testes realmente exercitam o comportamento novo, inclusive caminhos de erro e limites. Não considere a simples existência de testes como prova de correção.
- Reporte primeiro os achados, ordenados por severidade, com arquivo e linha, impacto e correção recomendada. Separe bloqueadores de sugestões e evite comentários puramente estilísticos sem efeito prático.
- Se não houver defeitos, declare isso explicitamente e registre riscos residuais ou validações que não puderam ser executadas. Não aprove uma mudança enquanto houver achado bloqueador sem tratamento.

### Agente de testes

- Valide comportamento, regressões, compatibilidade de configuração e tratamento de falhas; não faça refatorações alheias ao escopo.
- Considere `make tests` a execução oficial da suíte no contêiner. A CI reproduz o fluxo `make run` seguido de `make tests`.
- Não use uma execução direta no host como resultado definitivo: sem `RO_DOU__DAG_CONF_DIR`, timezone do Airflow e metadatabase migrada, ela pode produzir falsos negativos.
- Cubra sucesso, erro e limites. Use mocks para HTTP, SMTP, Slack, Discord, bancos e provedores de IA. Testes devem ser determinísticos e independentes de data corrente, ordem, internet e credenciais reais.
- Para mudanças em YAML/modelos, execute `test_validate_yaml_schemas.py`, `parsers_test.py` e `test_dag_loading.py`; para geração/orquestração, inclua `dag_generator_test.py` e, quando pertinente, `test_e2e_dag_execution.py`.
- Para buscadores, hooks, notificadores ou IA, execute primeiro o arquivo correspondente e depois `make tests` se o ambiente permitir.
- Não há `pytest-cov` nem limite mínimo de cobertura configurado; não alegue percentual de cobertura sem medição própria verificável. Áreas atualmente sem cobertura direta identificada incluem `inlabs_hook_sql_mode`, cliente/indexador/pipeline do OpenSearch, `templateManager`, `executive_summary` e o pipeline real da DAG de carga do INLABS; priorize-as quando forem tocadas.
- Falha causada por ambiente ou serviço ausente não deve ser ocultada: registre o comando, a mensagem essencial e o que falta para reproduzir.

Baseline verificada em 15/09/2026: 358 testes passaram em 10,02 s, sem warnings, em contêiner efêmero configurado como o ambiente Airflow. Esse número é uma referência histórica, não substitui a execução após cada mudança e pode crescer conforme a suíte evoluir.

### Agente de documentação

- Atualize `README.md` apenas para visão geral; detalhes de uso pertencem a `docs/docs/`.
- Ao adicionar página, inclua-a na navegação de `docs/mkdocs.yml`. Preserve links relativos, idioma português e terminologia usada na interface/Airflow.
- Mantenha parâmetros documentados alinhados aos defaults e validadores de `src/schemas.py`, e exemplos alinhados aos YAMLs válidos.
- Não edite `docs/docs/changelog/changelog.md` diretamente para uma mudança comum; o workflow o deriva de `CHANGELOG.md` durante a publicação.
- Construa a documentação localmente e confira avisos, links e blocos de código. Não publique no GitHub Pages.

## Segredos, dados e operações destrutivas

- Não leia nem exiba arquivos de segredo sem necessidade estrita. Nunca versionar `.env`, `.airflow_token`, `values-local.yaml`, credenciais, tokens, dumps ou dados de produção.
- Use placeholders inequívocos em exemplos. Não copie as credenciais locais de desenvolvimento para configurações reais.
- Não apague volumes, bancos, logs, contêineres, branches ou arquivos existentes sem autorização explícita. `make down` desliga serviços; qualquer remoção de volumes exige confirmação separada.
- Não sobrescreva alterações concorrentes. Se outro agente tocar o mesmo trecho, coordene a integração em vez de restaurar o arquivo inteiro.
- Não use dados pessoais de publicações reais como fixture quando dados sintéticos forem suficientes.

## Critérios de conclusão

Uma mudança está pronta quando:

- o comportamento solicitado foi implementado sem ampliar indevidamente o escopo;
- contratos de YAML, DAGs, integrações e compatibilidade foram considerados;
- testes novos ou ajustados cobrem a mudança e os testes aplicáveis passam;
- exemplos e documentação pública refletem qualquer alteração observável;
- nenhum segredo, cache, dado local ou arquivo alheio entrou no diff;
- riscos de segurança e limitações remanescentes foram registrados;
- o relatório final lista arquivos alterados, validações executadas e resultados, além de qualquer validação não executada e seu motivo.
