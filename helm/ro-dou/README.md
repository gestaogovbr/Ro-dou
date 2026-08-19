# Chart Helm do Ro-DOU

Este chart instala o Ro-DOU no Kubernetes com Airflow 3, PostgreSQL,
SMTP4dev e OpenSearch opcional.

## Pré-requisitos

- Kubernetes 1.19 ou superior
- Helm 3.0 ou superior
- Uma `StorageClass` compatível com as configurações de persistência do chart
- Para executar o OpenSearch no cluster, `vm.max_map_count` deve ser pelo menos
  `262144` no nó

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

## Configuração

Os principais valores configuráveis são:

| Parâmetro | Descrição | Valor padrão |
| --- | --- | --- |
| `airflow.image.repository` | Repositório da imagem do Airflow/Ro-DOU | `ghcr.io/gestaogovbr/ro-dou` |
| `airflow.image.tag` | Tag da imagem do Airflow/Ro-DOU | `latest` |
| `airflow.image.pullPolicy` | Política de download da imagem | `IfNotPresent` |
| `airflow.apiServer.replicas` | Réplicas do servidor de API | `1` |
| `airflow.apiServer.port` | Porta do servidor de API | `8080` |
| `airflow.apiServer.service.type` | Tipo do Service do servidor de API | `ClusterIP` |
| `airflow.apiServer.ingress.enabled` | Cria um Ingress para a interface e API do Airflow | `false` |
| `airflow.apiServer.ingress.className` | Nome da `IngressClass` | `""` |
| `airflow.apiServer.ingress.annotations` | Anotações adicionadas ao Ingress | `{}` |
| `airflow.apiServer.ingress.hosts` | Hosts e caminhos publicados pelo Ingress | `airflow.local` |
| `airflow.apiServer.ingress.tls` | Configuração TLS do Ingress | `[]` |
| `airflow.scheduler.replicas` | Réplicas do scheduler | `1` |
| `airflow.dagProcessor.replicas` | Réplicas do processador de DAGs | `1` |
| `airflow.pvc.storage` | Espaço solicitado para os logs do Airflow | `1Gi` |
| `airflow.pvc.storageClassName` | `StorageClass` usada pelos logs do Airflow | `""` |
| `gitRsync.enabled` | Sincroniza as configurações das DAGs de um repositório Git | `false` |
| `gitRsync.schedule` | Agendamento do CronJob de sincronização | `*/5 * * * *` |
| `gitRsync.repository` | URL HTTPS do repositório Git | `""` |
| `gitRsync.branch` | Branch sincronizada | `main` |
| `gitRsync.targetDir` | Diretório montado nos componentes do Airflow | `/opt/airflow/dags/ro_dou/dag_confs` |
| `gitRsync.targetOwner.uid` | UID proprietário do diretório e dos arquivos sincronizados | `50000` |
| `gitRsync.targetOwner.gid` | GID proprietário do diretório e dos arquivos sincronizados | `0` |
| `gitRsync.secret.name` | Secret existente que contém o token Git; vazio para repositórios públicos | `""` |
| `gitRsync.secret.key` | Chave do token dentro do Secret | `token` |
| `gitRsync.persistence.existingClaim` | PVC existente para os arquivos sincronizados; vazio cria um PVC | `""` |
| `gitRsync.persistence.storage` | Espaço solicitado para as configurações das DAGs | `1Gi` |
| `gitRsync.persistence.storageClassName` | `StorageClass` usada pelas configurações das DAGs | `""` |
| `gitRsync.persistence.accessMode` | Modo de acesso do PVC das configurações das DAGs | `ReadWriteOnce` |
| `airflow.secrets.AIRFLOW__CORE__FERNET_KEY` | Chave Fernet usada pelo Airflow | valor de desenvolvimento |
| `airflow.secrets.AIRFLOW__API_AUTH__JWT_SECRET` | Chave de assinatura dos tokens JWT | valor de desenvolvimento |
| `airflow.secrets.AIRFLOW__API__SECRET_KEY` | Chave secreta do servidor de API | valor de desenvolvimento |
| `airflow.secrets._AIRFLOW_WWW_USER_USERNAME` | Usuário administrador inicial | `admin` |
| `airflow.secrets._AIRFLOW_WWW_USER_PASSWORD` | Senha do administrador inicial | `admin` |
| `airflow.secrets.AIRFLOW__SMTP__SMTP_HOST` | Host SMTP externo; vazio usa o SMTP4dev deste release | `""` |
| `airflow.secrets.OPENSEARCH_USER` | Usuário utilizado para acessar o OpenSearch | `OPENSEARCH_USER` |
| `airflow.secrets.OPENSEARCH_PASS` | Senha do OpenSearch e senha inicial do administrador | `OPENSEARCH_PASS` |
| `postgres.image.repository` | Repositório da imagem do PostgreSQL | `postgres` |
| `postgres.image.tag` | Tag da imagem do PostgreSQL | `15` |
| `postgres.service.port` | Porta do PostgreSQL | `5432` |
| `postgres.secrets.postgres-user` | Usuário do PostgreSQL | `postgres` |
| `postgres.secrets.postgres-password` | Senha do PostgreSQL | `postgres` |
| `postgres.secrets.postgres-db` | Banco de metadados do Airflow | `airflow` |
| `postgres.storage` | Espaço solicitado para os dados do PostgreSQL | `1Gi` |
| `smtp4dev.enabled` | Implanta o SMTP4dev no cluster | `true` |
| `smtp4dev.image.repository` | Repositório da imagem do SMTP4dev | `rnwood/smtp4dev` |
| `smtp4dev.image.tag` | Tag da imagem do SMTP4dev | `v3` |
| `smtp4dev.service.webPort` | Porta da interface web do SMTP4dev | `5001` |
| `opensearch.enabled` | Implanta o OpenSearch no cluster | `false` |
| `opensearch.image.repository` | Repositório da imagem do OpenSearch | `opensearchproject/opensearch` |
| `opensearch.image.tag` | Tag da imagem do OpenSearch | `2` |
| `opensearch.service.port` | Porta HTTP do OpenSearch | `9200` |
| `opensearch.connection.enabled` | Habilita o uso do OpenSearch pelo Ro-DOU | `false` |
| `opensearch.connection.host` | URL de um OpenSearch externo; vazio usa o Service deste release | `""` |
| `opensearch.security.disablePlugin` | Desabilita o plugin de segurança | `true` |
| `opensearch.persistence.storage` | Espaço solicitado para os dados do OpenSearch | `1Gi` |
| `opensearch.persistence.storageClassName` | `StorageClass` dos dados do OpenSearch | `""` |

Consulte [`values.yaml`](./values.yaml) para ver todos os valores disponíveis.

## Exposição do Airflow por Ingress

Por padrão, o servidor de API e a interface do Airflow são expostos apenas por
um Service `ClusterIP`. Para criar também um Ingress:

```yaml
airflow:
  config:
    AIRFLOW__API__BASE_URL: https://airflow.exemplo.gov.br
  apiServer:
    ingress:
      enabled: true
      className: nginx
      annotations: {}
      hosts:
        - host: airflow.exemplo.gov.br
          paths:
            - path: /
              pathType: Prefix
      tls:
        - secretName: airflow-tls
          hosts:
            - airflow.exemplo.gov.br
```

O controlador de Ingress e o Secret TLS devem existir no cluster. Se TLS não
for necessário, mantenha `tls: []` e use a URL HTTP correspondente em
`AIRFLOW__API__BASE_URL`.

## Configuração de SMTP

Por padrão, `airflow.secrets.AIRFLOW__SMTP__SMTP_HOST` fica vazio. Nesse caso,
o chart configura automaticamente o endereço do serviço SMTP4dev criado para
o release, por exemplo `meu-rodou-ro-dou-smtp4dev`.

Para não implantar o SMTP4dev, defina `smtp4dev.enabled: false` e informe o
host de um servidor SMTP externo:

```yaml
smtp4dev:
  enabled: false

airflow:
  secrets:
    AIRFLOW__SMTP__SMTP_HOST: smtp.exemplo.gov.br
```

Para usar outro servidor de e-mail, informe o host e as demais credenciais em
um arquivo de valores:

```yaml
airflow:
  secrets:
    AIRFLOW__SMTP__SMTP_HOST: smtp.exemplo.gov.br
    AIRFLOW__SMTP__SMTP_PORT: "587"
    AIRFLOW__SMTP__SMTP_STARTTLS: "true"
    AIRFLOW__SMTP__SMTP_USER: usuario
    AIRFLOW__SMTP__SMTP_PASSWORD: senha
    AIRFLOW__SMTP__SMTP_MAIL_FROM: rodou@exemplo.gov.br
```

## Configuração do OpenSearch

O OpenSearch e sua integração com o Ro-DOU ficam desabilitados por padrão.
Para implantar a instância `single-node` incluída no chart e habilitar seu uso:

```yaml
opensearch:
  enabled: true
  connection:
    enabled: true

airflow:
  secrets:
    OPENSEARCH_USER: usuario
    OPENSEARCH_PASS: senha-segura
```

Quando `opensearch.connection.host` fica vazio, o chart configura o Airflow
com a URL interna do Service criado para o release, por exemplo
`http://rodou-ro-dou-opensearch:9200`.

Para utilizar uma instalação externa, mantenha `opensearch.enabled: false` e
informe a URL externa:

```yaml
opensearch:
  enabled: false
  connection:
    enabled: true
    host: https://opensearch.exemplo.gov.br

airflow:
  secrets:
    OPENSEARCH_USER: usuario
    OPENSEARCH_PASS: senha-segura
```

## Sincronização das configurações das DAGs via Git

O git-rsync é desabilitado por padrão. Quando habilitado, o chart cria um
CronJob e, salvo quando `existingClaim` é informado, um PVC dedicado. Esse PVC
é montado no servidor de API, scheduler e processador de DAGs do Airflow. Após
cada sincronização, o CronJob define o proprietário do diretório e de seus
arquivos como UID `50000` e GID `0`, usados pela imagem oficial do Airflow.

Para um repositório público:

```yaml
gitRsync:
  enabled: true
  repository: https://github.com/sua-organizacao/dag-confs.git
  branch: main
```

Para um repositório privado, crie previamente um Secret com um token HTTPS e
informe seu nome:

```bash
kubectl create secret generic git-token --from-literal=token=SEU_TOKEN
```

```yaml
gitRsync:
  enabled: true
  repository: https://github.com/sua-organizacao/dag-confs.git
  secret:
    name: git-token
    key: token
```


## Serviços

- **Servidor de API do Airflow:** porta 8080, incluindo a interface web e a API
- **PostgreSQL:** porta 5432
- **SMTP4dev:** interface web na porta 5001, SMTP na porta 25 e IMAP na porta 143
- **OpenSearch opcional:** API HTTP na porta 9200

O Airflow 3 executa o servidor de API, o scheduler e o processador de DAGs em
componentes separados.

Para acessar a interface do Airflow localmente:

```bash
kubectl port-forward service/rodou-ro-dou-airflow-api-server 8080:8080
```

Para acessar a interface do SMTP4dev:

```bash
kubectl port-forward service/rodou-ro-dou-smtp4dev 5001:5001
```

## Persistência

O chart cria um PVC para os logs do Airflow, um volume persistente para os
dados do PostgreSQL e, quando habilitados, volumes para o OpenSearch e o
git-rsync. Ajuste a `StorageClass`, o modo de acesso e o tamanho dos volumes de
acordo com o cluster antes da instalação.
