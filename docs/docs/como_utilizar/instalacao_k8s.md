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
`AIRFLOW__API_AUTH__JWT_SECRET`, entre outros), além das senhas padrão de
PostgreSQL e OpenSearch. Sobrescreva todos esses valores no seu
`my-values.yaml` antes de instalar em um ambiente real.
