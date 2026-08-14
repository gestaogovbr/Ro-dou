# Ro-DOU on Kubernetes

Instruções para subir o Ro-DOU em um cluster Kubernetes 🚀🚀🚀

## Helm deploy

Em breve...

## Manual deployment

## Pré-requisitos

- Um cluster Kubernetes local e o `kubectl` configurado.
- A imagem `ghcr.io/gestaogovbr/ro-dou:latest` acessível pelo cluster. Os
  componentes do Airflow usam `imagePullPolicy: Always` para resolver a tag
  novamente sempre que um pod for criado.
- Capacidade de provisionar volumes `ReadWriteOnce`.
- Para o OpenSearch, `vm.max_map_count` deve ser pelo menos `262144` no nó.

Os exemplos abaixo usam o namespace `airflow-rodou`:

```bash
kubectl create namespace airflow-rodou
```

Antes do deploy, preencha os valores adequados em
`airflow/airflow-secrets.yml` e `postgres/postgres-secrets.yml`.

## Instalação

1. Suba PostgreSQL e aguarde sua disponibilidade:

   ```bash
   kubectl -n airflow-rodou apply -f postgres/postgres-secrets.yml
   kubectl -n airflow-rodou apply -f postgres/postgres-deployment.yml
   kubectl -n airflow-rodou rollout status statefulset/postgres
   ```

2. Crie o banco usado pelo INLABS:

   ```bash
   kubectl -n airflow-rodou apply -f postgres/postgres-inlabsdb-configmap.yml
   kubectl -n airflow-rodou apply -f postgres/postgres-create-inlabsdb-job.yml
   kubectl -n airflow-rodou wait --for=condition=complete job/init-inlabs-db --timeout=120s
   ```

3. Suba os serviços auxiliares e a configuração do Airflow:

   ```bash
   kubectl -n airflow-rodou apply -f airflow/airflow-secrets.yml
   kubectl -n airflow-rodou apply -f airflow/airflow-configmap.yml
   kubectl -n airflow-rodou apply -f airflow/airflow-pvc.yml
   ```

4. Migre o banco de metadados e crie o usuário administrador:

   ```bash
   kubectl -n airflow-rodou apply -f airflow/airflow-init-db-job.yml
   kubectl -n airflow-rodou wait --for=condition=complete job/airflow-db-init --timeout=300s
   kubectl -n airflow-rodou apply -f airflow/airflow-create-admin-job.yml
   kubectl -n airflow-rodou wait --for=condition=complete job/airflow-create-admin --timeout=120s
   ```

5. Suba os componentes do Airflow 3:

   ```bash
   kubectl -n airflow-rodou apply -f airflow/airflow-api-server-deployment.yml
   kubectl -n airflow-rodou apply -f airflow/airflow-scheduler-deployment.yml
   kubectl -n airflow-rodou apply -f airflow/airflow-dag-processor-deployment.yml
   ```

6. Crie a conexão do portal INLABS:

   ```bash
   kubectl -n airflow-rodou apply -f airflow/airflow-create-inlabs-conn-job.yml
   kubectl -n airflow-rodou wait --for=condition=complete job/create-inlabs-portal-connection --timeout=120s
   ```
7. Crie as variáveis de ambiente:

   Edite o arquivo `airflow/airflow-create-variables.yml` com os nomes e valores das variáveis desejadas.

   ```bash
   kubectl -n airflow-rodou apply -f airflow/airflow-create-variables.yml
   ```

## Serviços opcionais

### OpenSearch

- O Ro-DOU não usa OpenSearch por padrão. Para habilitar, altere
  `RO_DOU_INLABS_USE_OPENSEARCH` para `true` no ConfigMap
  `airflow/airflow-configmap.yml`.
- Deploy (opcional):

```bash
kubectl -n airflow-rodou apply -f opensearch/opensearch-deployment.yml
kubectl -n airflow-rodou rollout status statefulset/opensearch
```

### SMTP4dev

- SMTP4dev é útil apenas para testes de envio de email. Deploy (opcional):

```bash
kubectl -n airflow-rodou apply -f smtp4dev/smtp4dev-deployment.yml
```

Exemplo de acesso local (opcional):

```bash
kubectl -n airflow-rodou port-forward service/smtp4dev 5001:5001
```

## Acesso local

Interface do Airflow:

```bash
kubectl -n airflow-rodou port-forward service/airflow-api-server 8080:8080
```

Acesse `http://localhost:8080` com o usuário e a senha definidos por
`_AIRFLOW_WWW_USER_USERNAME` e `_AIRFLOW_WWW_USER_PASSWORD`.


Jobs são imutáveis no Kubernetes. Para executá-los novamente, exclua o Job
correspondente antes de reaplicar o manifest.

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


