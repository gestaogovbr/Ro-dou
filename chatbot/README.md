# Chatbot REST do Ro-DOU

Aplicação independente para consultas em linguagem natural sobre publicações do
Diário Oficial da União. Esta implementação usa somente HTTP/REST e **não usa
MCP**. A pasta `mcp/` serviu apenas como referência de integração e não é uma
dependência deste serviço.

## Arquitetura

```text
Frontend (5174)
  -> POST /api/v1/chat
  -> ChatService
  -> LLMProvider.parse_search_intent()
  -> SearchIntent validado
  -> PublicationSearchService
  -> PostgreSQL ou OpenSearch
  -> resposta determinística
```

A LLM recebe somente a mensagem, a data atual, a identidade disponível e a
última intenção estruturada. Ela não recebe publicações, credenciais, DSN,
nomes de índice ou consultas. SQL e OpenSearch DSL são produzidos apenas dentro
de `PublicationSearchService`, a partir de campos validados e allowlists.

Os mesmos serviços sustentam duas interfaces:

- `POST /api/v1/chat`: interpretação em linguagem natural e conversa;
- `POST /api/v1/publications/search`: pesquisa estruturada reutilizável.

Não há chamada HTTP interna entre essas rotas: ambas reutilizam diretamente a
mesma instância de `PublicationSearchService`.

## Execução com Docker

Mantenha a rede e o PostgreSQL da stack principal disponíveis e execute:

```bash
cd /opt/Ro-dou
cp chatbot/config.example.yaml chatbot/config.yaml
export RO_DOU_CHAT_AI_PROVIDER=openai
export RO_DOU_CHAT_AI_MODEL=gpt-4.1-mini
export RO_DOU_CHAT_AI_API_KEY='configure-em-um-secret-manager'
docker compose -f chatbot/docker-compose.yml up --build
```

O frontend estará em `http://localhost:5174` e a API em
`http://localhost:8001`. A documentação OpenAPI fica em
`http://localhost:8001/docs`.

As portas são vinculadas a `127.0.0.1` por padrão. Para um ambiente protegido
por proxy/autenticação, `RO_DOU_CHAT_BIND_ADDRESS` pode definir outro endereço.

O Dockerfile usa `config.example.yaml` como configuração padrão sem alterá-lo.
A cópia local para `config.yaml` é útil quando a API for executada fora do
contêiner; selecione-a com `RO_DOU_CHAT_CONFIG=chatbot/config.yaml`.

## Configuração

Configurações não sensíveis ficam em `config.yaml`, com a estrutura demonstrada
em `config.example.yaml`. Variáveis de ambiente têm precedência:

- `RO_DOU_CHAT_ENABLED`;
- `RO_DOU_CHAT_AI_PROVIDER`: `openai`, `anthropic` ou `gemini`;
- `RO_DOU_CHAT_AI_MODEL`;
- `RO_DOU_CHAT_AI_TEMPERATURE`;
- `RO_DOU_CHAT_AI_TIMEOUT`;
- `RO_DOU_CHAT_MAX_RESULTS`;
- `RO_DOU_CHAT_MAX_CONCURRENT_AI_CALLS`;
- `RO_DOU_CHAT_SEARCH_SOURCE`: `postgres` ou `opensearch`;
- `RO_DOU_CHAT_SEARCH_TIMEOUT`;
- `INLABS_POSTGRES_DSN` e `INLABS_TABLE`;
- `OPENSEARCH_HOST`, `OPENSEARCH_INDEX` e `OPENSEARCH_USER`;
- `RO_DOU_TIMEZONE`.

Segredos são aceitos somente pelo ambiente:

- `RO_DOU_CHAT_AI_API_KEY`;
- `RO_DOU_CHAT_API_TOKEN`;
- `OPENSEARCH_PASS`.

O carregador rejeita esses valores quando aparecem no YAML.

## API

Consulta conversacional direta na API:

```http
POST /api/v1/chat
Content-Type: application/json
Authorization: Bearer configure-o-token-da-api
X-User-Name: Eduardo Lauer

{
  "message": "Quais publicações referentes ao meu nome constam no DOU hoje?",
  "conversation_id": null,
  "client_id": "b94aa54d-b8ca-4a04-82d6-4e606c131f89"
}
```

O `conversation_id` e o `client_id` retornados devem ser reenviados nas mensagens
seguintes. O backend vincula a conversa ao principal autenticado ou ao
`client_id` anônimo, e rejeita reutilização por outro proprietário. Ele guarda
somente a última intenção, filtros e IDs dos últimos resultados, com limite de
quantidade e expiração. O histórico textual integral não é usado como fonte de
controle.

Pesquisa estruturada:

```http
POST /api/v1/publications/search
Content-Type: application/json

{
  "terms": ["dengue"],
  "excluded_terms": ["licitação"],
  "organizations": ["Ministério da Saúde"],
  "limit": 20
}
```

Todas as buscas são limitadas pelo backend à data atual de
`RO_DOU_TIMEZONE`. Valores de `date_from` e `date_to` enviados pelo cliente ou
interpretados pela LLM são substituídos pela data de hoje; publicações de dias
anteriores nunca são retornadas. Quando não houver correspondência hoje, a
resposta informa explicitamente que não há publicações no dia de hoje. A rota
estruturada também retorna `effective_date` com a data efetivamente consultada e
`message` quando a lista estiver vazia.

Quando o total encontrado ultrapassa `chat.max_results` (ou
`RO_DOU_CHAT_MAX_RESULTS`) e o limite solicitado alcança ou excede esse teto, o
backend retorna em `message` um aviso com o limite aplicado. O chat exibe esse
aviso antes da lista e informa que apenas as primeiras publicações serão
apresentadas. Uma requisição que solicite deliberadamente menos itens não é
tratada como estouro do limite configurado.

## Logs persistentes

O backend grava arquivos texto em JSON Lines na pasta `chatbot/logs`, mapeada
no contêiner como `/app/logs`:

- `chat-history.txt`: mensagem, resposta, identidade autenticada quando houver,
  IDs da conversa/cliente e intenção estruturada;
- `sql-queries.txt`: comandos SQL parametrizados gerados pela camada de busca,
  com instrução e parâmetros separados.

Tokens, chaves, DSN e senhas não são registrados. Os arquivos usam rotação,
configurável por `RO_DOU_CHAT_LOG_MAX_BYTES` (padrão `10000000`) e
`RO_DOU_CHAT_LOG_BACKUP_COUNT` (padrão `5`). O diretório pode ser alterado por
`RO_DOU_CHAT_LOG_DIR` e o recurso desativado com
`RO_DOU_CHAT_LOG_ENABLED=false`.

Ambos os arquivos podem conter nomes e outros dados pessoais: no histórico,
eles podem estar nas consultas e respostas; no log SQL, podem aparecer nos
parâmetros da pesquisa. O backend cria o diretório com modo `0700` e os arquivos
com `0600`. Ainda assim, defina retenção compatível com a política da organização
e não versione esses arquivos; a raiz do repositório os ignora explicitamente.

A rotação em arquivo pressupõe um único processo gravador. A imagem fixa o
Uvicorn em um worker. Não compartilhe o mesmo diretório de logs entre réplicas;
para múltiplas réplicas, use volumes separados ou um coletor de logs externo.

Cada item retornado inclui `content` e `content_type`. Quando a publicação
possui ementa válida, `content_type` é `ementa` e o conteúdo integral da ementa
é exibido. Caso contrário, `content_type` é `excerpt` e o backend produz um
recorte do texto centralizado no termo pesquisado; na busca por OpenSearch, o
fragmento de destaque da própria fonte é aproveitado. A resposta conversacional
identifica explicitamente cada conteúdo como `Ementa` ou `Recorte`, e o frontend
o apresenta em um box separado do título/link da publicação.

Quando `RO_DOU_CHAT_API_TOKEN` estiver configurado, ambas as rotas exigem
`Authorization: Bearer <token>`. O frontend não possui campo para token: o
proxy do servidor Vite lê `RO_DOU_CHAT_API_TOKEN` no ambiente e injeta o Bearer
ao encaminhar `/api`, sem incluir a credencial no JavaScript entregue ao
navegador. O nome também não é solicitado no formulário; em produção, uma
camada same-origin autenticada deve fornecer `X-User-Name`. Sem token
configurado, a API permite consultas públicas locais, mas ignora
`X-User-Name`.

## Data e conversa

O backend calcula o dia atual deterministicamente com `RO_DOU_TIMEZONE` e
substitui qualquer outro período antes de consultar PostgreSQL ou OpenSearch.

Uma continuação como “Só do MGI” reutiliza filtros apenas quando o provider
retorna a decisão estruturada `context_action=refine`. Novas consultas usam
`replace`. O campo validado `clear_filters` permite remover explicitamente
termos, órgãos, seções, campo ou datas da intenção anterior.

Siglas conhecidas são expandidas pelo backend antes da busca. Inicialmente são
suportadas `MGI` e `ANVISA`, mapeadas para os nomes oficiais usados em
`artcategory`.

## Testes

Os testes não chamam providers reais nem serviços externos:

```bash
docker compose -f chatbot/docker-compose.yml run --rm --no-deps \
  --entrypoint sh chatbot-backend \
  -c "pip install --quiet pytest && pytest -q /app/chatbot/tests"

docker compose -f chatbot/docker-compose.yml run --rm --no-deps \
  --entrypoint sh chatbot-frontend -c "npm run build"
```
