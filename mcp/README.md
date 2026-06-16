# Stack MCP do Chatbot Ro-DOU

Esta pasta contém a arquitetura interativa do chatbot do Ro-DOU.
O servidor MCP expõe ferramentas reutilizáveis sobre os dados de diários
para clientes interativos.

## Componentes

- `server/`: servidor MCP do Ro-DOU. Ele concentra o acesso ao OpenSearch e a
  configuração dos provedores de IA.
- `backend/`: API FastAPI do chatbot. Ela usa o cliente Python MCP para chamar
  o servidor MCP e expõe `/api/chat` para os navegadores.
- `frontend/`: página do chatbot em TypeScript. Ela chama apenas o backend
  FastAPI.

## Fluxo de dados

```text
página do chatbot
  -> FastAPI /api/chat
  -> cliente Python MCP
  -> servidor MCP Ro-DOU
  -> OpenSearch / provedores de IA
```

O frontend nunca chama o servidor MCP diretamente e nunca recebe chaves de API
dos provedores de IA. A seleção do provedor e as credenciais são configuradas
somente no ambiente do servidor MCP.

## Docker Compose

Antes de subir o chatbot, mantenha a infraestrutura principal do Ro-DOU ativa a
partir da raiz do projeto:

```bash
cd /opt/Ro-dou
docker compose up -d postgres
```

Depois, execute a stack do chatbot a partir desta pasta:

```bash
cd /opt/Ro-dou/mcp
docker compose up --build mcp-frontend
```

Abra a página do chatbot em `http://localhost:5173`. O navegador chama o
backend FastAPI em `http://localhost:8000`; o backend chama o servidor MCP pela
rede Docker.

Execute a stack do chatbot com OpenSearch habilitado:

```bash
cd /opt/Ro-dou
COMPOSE_PROFILES=enable_opensearch docker compose up -d postgres opensearch

cd /opt/Ro-dou/mcp
ENABLE_OPENSEARCH=true docker compose up --build mcp-frontend
```

Execute apenas o servidor MCP:

```bash
cd /opt/Ro-dou/mcp
docker compose up --build mcp-server
```

## Variáveis de ambiente

Servidor MCP:

- `ENABLE_OPENSEARCH`, padrão `false`. Quando `false`, a busca usa diretamente
  a tabela PostgreSQL do INLABS.
- `OPENSEARCH_HOST`, padrão `http://localhost:9200`
- `OPENSEARCH_USER`, opcional
- `OPENSEARCH_PASS`, opcional
- `OPENSEARCH_INDEX`, padrão `dou`
- `INLABS_POSTGRES_DSN`, padrão
  `postgresql://airflow:airflow@localhost:5432/inlabs`
- `INLABS_TABLE`, padrão `dou_inlabs.article_raw`
- `RO_DOU_DAY_CONTEXT_PUBLICATION_LIMIT`, padrão `1000`. Define o limite de
  publicações retornadas pela ferramenta de listagem por dia. Esse limite não é
  usado para montar contexto de IA.
- `RO_DOU_AI_CONTEXT_PUBLICATION_LIMIT`, padrão `20`. Define o número máximo de
  publicações previamente filtradas no PostgreSQL que podem entrar no contexto
  de IA.
- `RO_DOU_AI_CONTEXT_BODY_CHARS`, padrão `300`. Define quantos caracteres do
  texto de cada publicação entram no contexto.
- `RO_DOU_AI_PROVIDER`, opcional: `openai`, `gemini`, `claude` ou `azure`
- `RO_DOU_AI_MODEL`, opcional: modelo ou nome do deployment do provedor
- `RO_DOU_AI_API_KEY`, opcional: chave de API do provedor
- `AZURE_OPENAI_ENDPOINT`, obrigatório para Azure
- `AZURE_OPENAI_API_VERSION`, obrigatório para Azure

Backend FastAPI:

- `RO_DOU_MCP_SERVER_URL`, padrão `http://localhost:8100/sse`

Frontend:

- `VITE_RO_DOU_API_URL`, padrão `http://localhost:8000`

## Alternância do OpenSearch no Docker Compose

Por padrão, o servidor MCP busca diretamente no banco PostgreSQL do INLABS e o
serviço OpenSearch não é iniciado.

Busca via PostgreSQL:

```bash
docker compose up --build mcp-frontend
```

Busca via OpenSearch:

```bash
ENABLE_OPENSEARCH=true docker compose up --build mcp-frontend
```

O arquivo `mcp/docker-compose.yml` usa a rede externa `ro-dou_default` por
padrão para acessar os serviços da stack principal, como `postgres` e
`opensearch`. Se o nome da rede Docker for diferente no seu ambiente, defina:

```bash
RO_DOU_DOCKER_NETWORK=nome_da_rede docker compose up --build mcp-frontend
```
