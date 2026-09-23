# Ro-DOU on Kubernetes

Instruções para subir o Ro-DOU em um cluster Kubernetes 🚀🚀🚀

O deploy no Kubernetes é feito pelo chart Helm em `helm/ro-dou`, que instala
Airflow 3, PostgreSQL, SMTP4dev e, opcionalmente, OpenSearch e a
sincronização das configurações das DAGs via Git (git-rsync).

## Pré-requisitos

- Kubernetes 1.19 ou superior
- Helm 3.0 ou superior
- Uma `StorageClass` compatível com as configurações de persistência do chart
- Para executar o OpenSearch no cluster, `vm.max_map_count` deve ser pelo
  menos `262144` no nó

## Instalação

> **Atenção: altere as credenciais antes de usar em produção.**
> Os valores padrão do chart (chaves Fernet, JWT e da API, `admin`/`admin`,
> senhas do PostgreSQL e do OpenSearch) são de desenvolvimento e estão
> publicados no repositório. Sobrescreva-os em um `my-values.yaml` que não
> seja versionado, conforme a seção
> [Antes de usar em produção](#antes-de-usar-em-producao).

Para instalar o chart com o nome de release `rodou`:

```bash
helm install rodou ./helm/ro-dou
```

Para personalizar a instalação, crie um arquivo de valores e informe-o com
`-f`:

```bash
helm install rodou ./helm/ro-dou -f my-values.yaml
```

## Atualização

Para atualizar uma instalação existente:

```bash
helm upgrade rodou ./helm/ro-dou -f my-values.yaml
```

## Desinstalação

```bash
helm uninstall rodou
```

Os volumes persistentes podem permanecer no cluster após a desinstalação.
Verifique os PVCs antes de remover seus dados manualmente.

## Acesso local

Interface e API do Airflow:

```bash
kubectl port-forward service/rodou-ro-dou-airflow-api-server 8080:8080
```

Acesse `http://localhost:8080` com o usuário e a senha definidos por
`airflow.secrets._AIRFLOW_WWW_USER_USERNAME` e
`airflow.secrets._AIRFLOW_WWW_USER_PASSWORD` (padrão `admin`/`admin`).

Interface do SMTP4dev:

```bash
kubectl port-forward service/rodou-ro-dou-smtp4dev 5001:5001
```

## Sincronização dos `dag_confs` via Git (git-rsync)

Em ambientes onde o Ro-DOU roda no Kubernetes, é comum manter as
configurações das DAGs em uma pasta `dag_confs/`. Para sincronizar essas
configurações a partir de um repositório Git sem rebuildar imagens, há um
exemplo de solução `git-rsync` em `k8s/git-rsync/` que:

- provê um `ConfigMap` com um script `git-rsync.sh` que faz `git clone`/
   `git pull` e usa `rsync` para atualizar o diretório alvo;
- provê um `CronJob` que executa o script periodicamente (padrão: a cada
   5 minutos).

Como usar (passos rápidos):

1. Ajuste `k8s/git-rsync/git-rsync-cronjob.yml` definindo `GIT_REPO`,
    `GIT_BRANCH` e substitua `dag-confs-pvc` pelo nome do seu PVC destino.
2. Aplique os manifests:

```bash
kubectl -n airflow-rodou apply -f k8s/git-rsync/git-rsync-configmap.yml
kubectl -n airflow-rodou apply -f k8s/git-rsync/git-rsync-cronjob.yml
```

3. Para repositórios privados, prefira usar um token (PAT) via HTTPS:

```bash
kubectl -n airflow-rodou create secret generic git-token --from-literal=token=YOUR_GITHUB_TOKEN
kubectl -n airflow-rodou apply -f k8s/git-rsync/git-rsync-cronjob.yml
```

!!! warning "Quem pode editar os YAMLs"
    Os arquivos sincronizados viram DAGs sem outra revisão. Proteja a branch
    sincronizada e exija revisão da equipe responsável pelo Ro-DOU (por
    exemplo, com `CODEOWNERS`), principalmente para mudanças em
    `from_db_select`. Liste em `AIRFLOW_VAR_RO_DOU_ALLOWED_TERMS_CONN_IDS`
    apenas as conexões que as unidades podem consultar. Elas devem usar
    usuários de banco somente leitura, restritos às tabelas de termos.

## Configuração

A pasta `helm/ro-dou` contém um
[`README.md`](https://github.com/gestaogovbr/Ro-dou/blob/main/helm/ro-dou/README.md)
com mais informações: tabela de parâmetros, exposição por Ingress,
configuração de SMTP externo, OpenSearch e sincronização das configurações
das DAGs via Git (git-rsync).

Consulte também
[`helm/ro-dou/values.yaml`](https://github.com/gestaogovbr/Ro-dou/blob/main/helm/ro-dou/values.yaml)
para a lista completa de valores.

### Antes de usar em produção

O chart traz valores de desenvolvimento em `airflow.secrets`
(`AIRFLOW__CORE__FERNET_KEY`, usuário/senha `admin`/`admin`,
`AIRFLOW__API_AUTH__JWT_SECRET`, `AIRFLOW__API__SECRET_KEY`, credenciais de
SMTP e do INLABS, entre outros), além das senhas padrão de PostgreSQL
(`postgres.secrets`) e OpenSearch. Como esses valores são públicos, sobrescreva
**todos** no seu `my-values.yaml` antes de instalar em um ambiente real, não
versione esse arquivo e prefira Secrets gerenciados fora do repositório.

### OpenSearch em produção

> **Atenção: por padrão, o OpenSearch roda sem autenticação e sem TLS.**
> O chart inicia a instância opcional com `opensearch.security.disablePlugin: true`,
> o que desliga o plugin de segurança. Use-a apenas em desenvolvimento e testes.

Em produção, utilize um OpenSearch externo com o plugin de segurança e TLS
habilitados, com certificado válido:

```yaml
opensearch:
  enabled: false
  connection:
    enabled: true
    host: https://opensearch.exemplo.gov.br

airflow:
  secrets:
    OPENSEARCH_USER: "<usuario-dedicado>"
    OPENSEARCH_PASS: "<senha-forte>"
```

Com um `host` iniciado por `https://`, o Ro-DOU já usa TLS, mas por padrão não
valida o certificado do servidor. Defina a variável do Airflow
`OPENSEARCH_VERIFY_CERTS` com o valor `true`; o chart não a cria. Não use
`false`: a variável é lida como texto e qualquer valor não vazio conta como
verdadeiro. Prefira um usuário dedicado, com acesso restrito ao índice `dou`, e
restrinja o acesso de rede à porta do OpenSearch. Mais detalhes no
[README do chart](https://github.com/gestaogovbr/Ro-dou/blob/main/helm/ro-dou/README.md).
