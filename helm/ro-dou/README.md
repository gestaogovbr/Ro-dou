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
| `airflow.scheduler.replicas` | Réplicas do scheduler | `1` |
| `airflow.dagProcessor.replicas` | Réplicas do processador de DAGs | `1` |
| `airflow.pvc.storage` | Espaço solicitado para os logs do Airflow | `1Gi` |
| `airflow.pvc.storageClassName` | `StorageClass` usada pelos logs do Airflow | `""` |
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
`http://meu-rodou-ro-dou-opensearch:9200`.

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
dados do PostgreSQL e, quando habilitado, outro para o OpenSearch. Ajuste a
`StorageClass` e o tamanho dos volumes de acordo com o cluster antes da
instalação.

## Segredos

O chart fornece credenciais e chaves padrão apenas para facilitar ambientes de
desenvolvimento. Antes de uma instalação compartilhada ou de produção,
substitua as chaves do Airflow, o administrador inicial e as credenciais do
PostgreSQL em um arquivo de valores protegido:

```yaml
airflow:
  secrets:
    AIRFLOW__CORE__FERNET_KEY: <fernet-key>
    AIRFLOW__API_AUTH__JWT_SECRET: <jwt-secret>
    AIRFLOW__API__SECRET_KEY: <api-secret>
    _AIRFLOW_WWW_USER_USERNAME: <usuario-administrador>
    _AIRFLOW_WWW_USER_PASSWORD: <senha-administrador>

postgres:
  secrets:
    postgres-user: <usuario-postgresql>
    postgres-password: <senha-postgresql>
    postgres-db: airflow
```

Não versione o arquivo que contém os valores reais. Em ambientes de produção,
prefira ainda integrar o processo de instalação a um gerenciador externo de
segredos. Os valores padrão nunca devem ser reutilizados fora de ambientes de
desenvolvimento.
