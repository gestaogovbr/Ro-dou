# Gestão de DAGs pela interface do Airflow

Além do fluxo tradicional, em que os arquivos YAML ficam em um repositório git
sincronizado com o Ro-DOU, é possível criar, visualizar, alterar e excluir
DAGs direto pelo navegador, sem usar o git. A tela fica dentro do próprio
Airflow, no botão **Ro-DOU DAGs** do menu lateral, e usa o mesmo login.

## O que a tela permite

* **Listar** todas as DAGs do Ro-DOU, com filtro por id, descrição, arquivo e
  origem (criadas pela tela ou sincronizadas via git).
* **Visualizar** o YAML, a descrição, a agenda e os erros de validação de cada
  DAG, com atalho para abri-la no Airflow.
* **Criar** uma DAG pelo mesmo [formulário do gerador de YAML](../gerador_yaml.html)
  publicado nesta documentação, que já inclui Slack, Discord e Microsoft Teams,
  ou escrevendo o YAML diretamente.
* **Alterar** uma DAG criada pela tela, pelo formulário ou pelo YAML.
* **Duplicar** qualquer DAG (inclusive as do git) como ponto de partida de uma nova.
* **Excluir** uma DAG criada pela tela.

As DAGs sincronizadas via git continuam sendo geridas pelo repositório: a tela
as mostra, mas não permite alterá-las nem excluí-las.

O formulário cobre o caso mais comum: uma busca por arquivo, termos digitados,
e-mail e webhooks. Configurações com recursos que ele não representa (várias
buscas, IA, termos vindos de banco ou variável, outros canais do Apprise…) são
abertas direto na aba **YAML**, para que nada se perca ao salvar. Ao salvar
pelo formulário, os comentários (`#`) do YAML original não são mantidos.

Depois de salvar, o Airflow pode levar alguns minutos para processar a DAG
nova ou alterada.

## Como funciona

A tela é um plugin do Airflow (`plugins/ro_dou_dag_manager`). Os arquivos
criados por ela são gravados em um diretório próprio, definido por
`RO_DOU__DAG_MANAGER_DIR`, que precisa constar também em `RO_DOU__DAG_CONF_DIR`
(lista de diretórios separados por `:`) para que o gerador crie as DAGs:

```yaml
RO_DOU__DAG_CONF_DIR: /opt/airflow/dags/ro_dou/dag_confs:/opt/airflow/dags/ro_dou/dag_confs_ui
RO_DOU__DAG_MANAGER_DIR: /opt/airflow/dags/ro_dou/dag_confs_ui
```

Por ficar separado, esse diretório não é apagado pela sincronização via git. O
nome de cada arquivo é o id da DAG (`<dag.id>.yaml`), e o id precisa ser único
entre todas as fontes.

Sem `RO_DOU__DAG_MANAGER_DIR` o plugin não é ativado. Se o diretório não
estiver em `RO_DOU__DAG_CONF_DIR`, a tela mostra um aviso e bloqueia a criação
e a edição.

No ambiente local (`make run`), a tela já vem habilitada e os arquivos ficam em
`mnt/dag_confs_ui/`. No Kubernetes, habilite-a no chart Helm com
`dagManager.enabled: true` (veja o README do chart).

## Permissões e segurança

A tela usa as permissões do Airflow do usuário conectado:

| Ação | Permissão exigida |
|------|-------------------|
| Listar e visualizar uma DAG | leitura daquela DAG |
| Listar e visualizar um arquivo com erro (sem `dag.id` válido) | edição de todas as DAGs |
| Criar, alterar e excluir | edição de todas as DAGs e da DAG afetada |
| Usar `terms.from_db_select` | edição da conexão informada em `conn_id` |
| Usar `terms.from_airflow_variable` ou `ai_config.api_key_var` | leitura da variável informada |

Com o gerenciador de autenticação padrão (FAB), os perfis `Admin`, `Op` e
`User` podem editar DAGs, e só `Admin` e `Op` acessam conexões e variáveis.
Quem pode ver uma DAG mas não editá-la vê os endereços de webhook com o token
oculto (`https://host/***`).

Como a tela amplia quem pode criar DAGs, ela aplica regras além do schema:

* os canais de `report.notification` ficam restritos a `discord://`,
  `slack://` e ao Microsoft Teams via Workflows: a URL `https` gerada pelo
  fluxo ou `workflows://`, sempre com host em `logic.azure.com` ou
  `powerplatform.com`. Outros canais do
  Apprise continuam disponíveis pelo fluxo via git ou podem ser liberados
  definindo `RO_DOU__DAG_MANAGER_NOTIFICATION_SCHEMES` (lista separada por
  vírgulas, que substitui a lista padrão);
* a agenda (`schedule`) precisa ser uma expressão cron válida ou um preset
  como `@daily`;
* âncoras e aliases YAML (`&`/`*`) não são aceitos, e o arquivo é limitado a 256 KB;
* uma alteração só é gravada se o arquivo não tiver sido modificado por outra
  pessoa desde que foi aberto.

Cada criação, alteração e exclusão é registrada no log do api-server com o
usuário, a ação, o arquivo e o id da DAG.
