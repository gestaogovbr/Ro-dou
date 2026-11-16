# Ro-DOU em produção com Docker Compose

Este diretório contém um override de produção para o `docker-compose.yml` da
raiz. Ele **não é carregado automaticamente** pelo `make run`, porque fica em
um subdiretório. O ambiente local continua usando o compose de desenvolvimento.
**Não use `make run` em produção:** ele sobe o compose de desenvolvimento, com
portas públicas e smtp4dev. Sempre informe os dois `-f` nos comandos abaixo;
sem o override, o compose da raiz publica as portas no host.

O override:

- remove a publicação pública de PostgreSQL (5432), OpenSearch (9200) e
  smtp4dev (25, 143 e 5001);
- publica o Airflow apenas em `127.0.0.1:8080`;
- exige segredos fortes no `.env.production`;
- desativa o smtp4dev no perfil padrão e usa o SMTP real;
- usa o código embutido na imagem, sem montar `src`, `tests` ou `tools` do host;
- monta `dag_confs/` como somente leitura;
- isola PostgreSQL e OpenSearch em uma rede interna sem saída para a internet;
- adiciona limites de memória e rotação de logs do Docker.

## Pré-requisitos

- Docker Compose 2.24 ou superior (as tags `!override` são usadas para
  substituir as portas do compose base).
- `vm.max_map_count` de pelo menos 262144 se o OpenSearch for usado.
- Diretórios de dados com permissão adequada.

## 1. Configurar segredos

```bash
cp deploy/prod/.env.production.example deploy/prod/.env.production
chmod 600 deploy/prod/.env.production
```

Gere os valores:

```bash
# Chave Fernet do Airflow
python3 -c "import base64, os; print(base64.urlsafe_b64encode(os.urandom(32)).decode())"

# Demais segredos
openssl rand -hex 32
openssl rand -hex 24   # senha do banco, URL-safe
```

Preencha no mínimo:

- `AIRFLOW_FERNET_KEY`
- `AIRFLOW_WEBSERVER_SECRET_KEY`
- `AIRFLOW_API_JWT_SECRET`
- `AIRFLOW_API_SECRET_KEY`
- `AIRFLOW_DB_PASSWORD`
- `AIRFLOW_ADMIN_PASSWORD`
- `SMTP_HOST`, `SMTP_MAIL_FROM` e `AIRFLOW_CONN_SMTP_DEFAULT`
- `OPENSEARCH_PASS`

Não versione `.env.production`.

> **Banco já existente:** `AIRFLOW_DB_PASSWORD` não altera a senha de um
> volume PostgreSQL já inicializado, e trocar `AIRFLOW_FERNET_KEY` pode tornar
> ilegíveis conexões/variáveis criptografadas. Em uma instalação nova, use um
> `mnt/pgdata` vazio. Em uma migração, altere a senha do banco via SQL e
> mantenha a chave Fernet antiga.

## 2. Preparar os diretórios

```bash
mkdir -p mnt/airflow-logs mnt/pgdata
sudo chown -R 50000:0 mnt/airflow-logs
sudo chmod 750 mnt/airflow-logs
```

O container do Airflow roda com UID 50000 por padrão. Se você alterar
`AIRFLOW_UID`, ajuste o `chown` correspondente.

## 3. Validar a configuração

```bash
docker compose \
  --env-file deploy/prod/.env.production \
  -f docker-compose.yml \
  -f deploy/prod/docker-compose.override.yml \
  config >/dev/null
```

Se o comando falhar, confira as variáveis obrigatórias e a versão do Compose.

## 4. Subir a stack

```bash
docker compose \
  --env-file deploy/prod/.env.production \
  -f docker-compose.yml \
  -f deploy/prod/docker-compose.override.yml \
  up -d --build
```

Verifique:

```bash
docker compose \
  --env-file deploy/prod/.env.production \
  -f docker-compose.yml \
  -f deploy/prod/docker-compose.override.yml \
  ps

curl -fsS http://127.0.0.1:8080/api/v2/monitor/health
```

Acesse `http://127.0.0.1:8080` por um túnel SSH ou configure o Traefik.

As DAGs sobem pausadas por causa de `AIRFLOW_DAGS_PAUSED=true`. Ative apenas as
que já foram revisadas. O diretório `dag_confs/` é montado como somente leitura:
mantenha nele apenas os YAMLs de produção e gere novos arquivos fora do
servidor.

## 5. Publicar com Traefik (opcional)

Descubra o nome exato da rede do Traefik:

```bash
docker network ls
```

Defina `TRAEFIK_NETWORK`, `RO_DOU_HOST`, `TRAEFIK_ENTRYPOINT` e
`TRAEFIK_CERT_RESOLVER` no `.env.production`. Depois:

```bash
docker compose \
  --env-file deploy/prod/.env.production \
  -f docker-compose.yml \
  -f deploy/prod/docker-compose.override.yml \
  -f deploy/prod/docker-compose.traefik.yml \
  up -d
```

O arquivo do Traefik remove a publicação em `127.0.0.1:8080` e adiciona o
serviço à rede externa. Ajuste as labels se o seu Traefik usar outro
entrypoint, certificado manual ou middleware de autenticação.

### Traefik em `network_mode: host`

Se o Traefik roda em `network_mode: host` (como o template `traefik-pk7y`),
não existe uma rede externa `traefik`. Use o override específico:

```bash
docker compose \
  --env-file deploy/prod/.env.production \
  -f docker-compose.yml \
  -f deploy/prod/docker-compose.override.yml \
  -f deploy/prod/docker-compose.traefik-host.yml \
  up -d
```

O arquivo usa `ro-dou_default` como rede do projeto. Se você mudou
`COMPOSE_PROJECT_NAME`, ajuste `TRAEFIK_DOCKER_NETWORK` no `.env.production`.
Defina também `RO_DOU_HOST` e mantenha `TRAEFIK_ENTRYPOINT=websecure` e
`TRAEFIK_CERT_RESOLVER=letsencrypt` se forem os valores do seu Traefik.

## 6. Configuração pós-subida

- Crie as conexões `inlabs_db` e `inlabs_portal` no Airflow, se for usar o
  INLABS.
- Crie a variável `email_admin` se quiser receber falhas por e-mail.
- Se for usar o INLABS no modo SQL, crie a base e o schema:

```bash
docker compose \
  --env-file deploy/prod/.env.production \
  -f docker-compose.yml \
  -f deploy/prod/docker-compose.override.yml \
  exec -T postgres sh -c 'psql -U "$POSTGRES_USER" -f /sql/init-db.sql'
```

O `inlabs_db` deve apontar para o host `postgres`, porta `5432`, banco
`inlabs` (ou o valor configurado) e usuário/senha do banco. O `inlabs_portal`
é uma conexão HTTP para `https://inlabs.in.gov.br/` com as credenciais do
portal.

## 7. Backup e atualização

Backup lógico do banco do Airflow:

```bash
docker compose \
  --env-file deploy/prod/.env.production \
  -f docker-compose.yml \
  -f deploy/prod/docker-compose.override.yml \
  exec -T postgres sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB"' \
  | gzip > airflow-$(date +%F).sql.gz
```

Também proteja `mnt/airflow-logs` e, se usar OpenSearch, o volume
`opensearch-data`. Não copie `mnt/pgdata` com o PostgreSQL em execução.

Atualização:

```bash
git pull
docker compose \
  --env-file deploy/prod/.env.production \
  -f docker-compose.yml \
  -f deploy/prod/docker-compose.override.yml \
  build --pull
docker compose \
  --env-file deploy/prod/.env.production \
  -f docker-compose.yml \
  -f deploy/prod/docker-compose.override.yml \
  up -d
```

## Observações de segurança

- `AIRFLOW_ADMIN_PASSWORD` só é aplicado quando o banco é inicializado pela
  primeira vez. Se o banco já existe, redefina a senha:

  ```bash
  docker compose \
    --env-file deploy/prod/.env.production \
    -f docker-compose.yml \
    -f deploy/prod/docker-compose.override.yml \
    exec airflow-api-server \
    airflow users reset-password --username admin
  ```

- O OpenSearch do compose base mantém `DISABLE_SECURITY_PLUGIN=true`. Neste
  override ele não publica porta, mas continua sem TLS/autenticação. Para
  produção mais exigente, use um OpenSearch externo com TLS ou configure a
  segurança do OpenSearch.
- O container do OpenSearch sobe mesmo com
  `RO_DOU_INLABS_USE_OPENSEARCH=false`, porque o compose base o declara como
  dependência dos serviços do Airflow. Ele fica isolado e limitado a 3 GB por
  padrão. Para não subir, seria necessário um compose próprio sem esse serviço
  e sem o `depends_on`.
- Docker publica portas contornando regras do UFW. Mesmo com o UFW ativo,
  mantenha as portas em `127.0.0.1` ou use o firewall do provedor.
- O `smtp4dev` só sobe com `--profile dev`; em produção use o SMTP real.
- Fixe a versão do OpenSearch depois de validar; `OPENSEARCH_VERSION=2` não é
  uma versão imutável.
