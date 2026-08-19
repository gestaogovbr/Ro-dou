# Ro-dou no Kubernetes

Manifests para uma instalação local do Ro-DOU com Airflow 3, PostgreSQL,
OpenSearch (opcional), SMTP4dev (opcional) e git-rsync (opcional).

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

- provê um `ConfigMap` com um script `git-rsync.sh` que faz um clone raso e
   usa `rsync` para atualizar o diretório alvo;
- provê um `CronJob` que executa o script periodicamente (padrão: a cada
   5 minutos);
- provê um PVC dedicado e patches opcionais que o montam, somente para
   leitura, no servidor de API, scheduler e processador de DAGs do Airflow.

Como usar (passos rápidos):

1. Ajuste `k8s/git-rsync/git-rsync-cronjob.yml` definindo `GIT_REPO` e
    `GIT_BRANCH`. O manifesto `dag-confs-pvc.yml` cria, por padrão, um PVC de
    1 Gi chamado `dag-confs-pvc`; ajuste-o se precisar de outra capacidade,
    classe de armazenamento ou modo de acesso.
2. Para um repositório privado, crie um Secret com um token (PAT) HTTPS. Um
    PAT classic precisa apenas do escopo `repo`; o escopo `user` não é
    necessário. Pule este passo para repositórios públicos:

```bash
kubectl -n airflow-rodou create secret generic git-token --from-literal=token=YOUR_GITHUB_TOKEN
```

3. Aplique os manifests:

```bash
kubectl -n airflow-rodou apply -f k8s/git-rsync/dag-confs-pvc.yml
kubectl -n airflow-rodou apply -f k8s/git-rsync/git-rsync-configmap.yml
kubectl -n airflow-rodou apply -f k8s/git-rsync/git-rsync-cronjob.yml
```

4. Aplique os patches para montar o PVC nos três Deployments do Airflow:

```bash
kubectl -n airflow-rodou patch deployment airflow-api-server --type=strategic --patch-file k8s/git-rsync/airflow-api-server-volume-patch.yml
kubectl -n airflow-rodou patch deployment airflow-scheduler --type=strategic --patch-file k8s/git-rsync/airflow-scheduler-volume-patch.yml
kubectl -n airflow-rodou patch deployment airflow-dag-processor --type=strategic --patch-file k8s/git-rsync/airflow-dag-processor-volume-patch.yml
```

O token é fornecido ao Git de forma não interativa por `GIT_ASKPASS`, sem ser
incluído na URL ou nos logs. Após cada sincronização, o CronJob altera o
proprietário do diretório e dos arquivos para UID `50000` e GID `0`, usados
pela imagem oficial do Airflow.

