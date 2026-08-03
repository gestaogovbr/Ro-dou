SHELL := /bin/bash
.PHONY: run
run: \
create-logs-dir \
build \
setup-containers \
get_access_token \
create-example-variable \
create-email-admim-variable \
create-path-tmp-variable \
create-inlabs-db \
create-inlabs-db-connection \
create-inlabs-portal-connection \
test-inlabs-db-connection \
create-opensearch-variable \
activate-inlabs-load-dag \
delete_token

.PHONY: create-azure-openai-variables
create-azure-openai-variables: \
get_access_token \
create-azure-openai-endpoint-variable \
create-azure-openai-api-version-variable \
create-azure-openai-deployment-variable \
create-azure-openai-api-key-variable \
delete_token

TOKEN_FILE := .airflow_token

get_access_token:
	@echo 'Waiting for Airflow API to start ...'
	@docker exec airflow-api-server sh -c "while ! curl -s 'http://localhost:8080/api/v2/monitor/health' > /dev/null; do sleep 5; done;"
	@echo "Obtendo token de acesso..."
	@curl -s -X POST 'http://localhost:8080/auth/token' \
		-H 'Content-Type: application/json' \
		-d '{"username":"airflow","password":"airflow"}' \
		| python3 -c 'import sys,json; print(json.load(sys.stdin).get("access_token",""))' > $(TOKEN_FILE)
	@TOKEN=$$(cat $(TOKEN_FILE)); \
	if [ -z "$$TOKEN" ]; then \
		echo "Erro: access_token vazio ou não retornado pela API. Abortando."; \
		rm -f $(TOKEN_FILE); \
		exit 1; \
	fi; \
	STATUS=$$(curl -s -o /dev/null -w "%{http_code}" \
		-H "Authorization: Bearer $$TOKEN" \
		'http://localhost:8080/api/v2/monitor/health'); \
	if [ "$$STATUS" != "200" ]; then \
		echo "Erro: token inválido (HTTP $$STATUS ao testar a API). Abortando."; \
		rm -f $(TOKEN_FILE); \
		exit 1; \
	fi; \
	echo "Token obtido e validado com sucesso."


create-logs-dir:
	mkdir -p ./mnt/airflow-logs -m a=rwx


AI_PROVIDERS ?=

build:
	@echo "AI_PROVIDERS=$(AI_PROVIDERS)"
	docker compose build \
		--build-arg AI_PROVIDERS="$(AI_PROVIDERS)"

setup-containers:
	docker compose up -d --force-recreate --remove-orphans

create-example-variable: get_access_token
	@echo "Creating 'termos_exemplo_variavel' Airflow variable"
	@TOKEN=$$(cat $(TOKEN_FILE)); \
	RESULT=$$(docker exec airflow-api-server sh -c \
		"curl -s -X 'POST' \
		'http://localhost:8080/api/v2/variables' \
		-H 'accept: application/json' \
		-H 'Content-Type: application/json' \
		-H 'Authorization: Bearer $$TOKEN' \
		-d '{ \
		\"key\": \"termos_exemplo_variavel\", \
		\"value\": \"LGPD\nlei geral de proteção de dados\nacesso à informação\" \
		}'"); \
	echo "$$RESULT" | grep -q "already exists" && echo "Variable already exists, skipping." || echo "$$RESULT"

create-email-admim-variable: get_access_token
	@echo "Creating 'email_admin_variavel' in Airflow variable"
	@TOKEN=$$(cat $(TOKEN_FILE)); \
	RESULT=$$(docker exec airflow-api-server sh -c \
		"curl -s -X 'POST' \
		'http://localhost:8080/api/v2/variables' \
		-H 'accept: application/json' \
		-H 'Content-Type: application/json' \
		-H 'Authorization: Bearer $$TOKEN' \
		-d '{ \
		\"key\": \"email_admin\", \
		\"value\": \"admim@rodou.gov.br\" \
		}'"); \
	echo "$$RESULT" | grep -q "already exists" && echo "Variable already exists, skipping." || echo "$$RESULT"

create-path-tmp-variable: get_access_token
	@echo "Creating 'path_tmp' Airflow variable"
	@TOKEN=$$(cat $(TOKEN_FILE)); \
	RESULT=$$(docker exec airflow-api-server sh -c \
		"curl -s -X 'POST' \
		'http://localhost:8080/api/v2/variables' \
		-H 'accept: application/json' \
		-H 'Content-Type: application/json' \
		-H 'Authorization: Bearer $$TOKEN' \
		-d '{ \
		\"key\": \"path_tmp\", \
		\"value\": \"/tmp\" \
		}'"); \
	echo "$$RESULT" | grep -q "already exists" && echo "Variable already exists, skipping." || echo "$$RESULT"

create-inlabs-db:
	@echo "Creating 'inlabs_db' database"
	@RESULT=$$(docker exec -e PGPASSWORD=airflow ro-dou-postgres-1 sh -c "psql -q -U airflow -f /sql/init-db.sql" 2>&1 1>/dev/null); \
	echo "$$RESULT" | grep -q "already exists" && echo "Database 'inlabs' already exists, skipping." || echo "$$RESULT"

create-inlabs-db-connection: get_access_token
	@echo "Creating 'inlabs_db' Airflow connection"
	@TOKEN=$$(cat $(TOKEN_FILE)); \
	RESULT=$$(docker exec airflow-api-server sh -c \
		"curl -s -X 'POST' \
		'http://localhost:8080/api/v2/connections' \
		-H 'accept: application/json' \
		-H 'Content-Type: application/json' \
		-H 'Authorization: Bearer $$TOKEN' \
		-d '{ \
		\"connection_id\": \"inlabs_db\", \
		\"conn_type\": \"postgres\", \
		\"schema\": \"inlabs\", \
		\"host\": \"ro-dou-postgres-1\", \
		\"login\": \"airflow\", \
		\"password\": \"airflow\", \
		\"port\": 5432 \
		}'"); \
	echo "$$RESULT" | grep -q "Unique constraint violation" && echo "Connection already exists (Unique constraint violation)." || echo "$$RESULT"


test-inlabs-db-connection:
	@echo "Testing 'inlabs_db' Airflow connection"
	@docker exec -e PYTHONWARNINGS=ignore airflow-scheduler airflow connections test inlabs_db

create-inlabs-portal-connection: get_access_token
	@echo "Creating 'inlabs_portal' Airflow connection"
	@TOKEN=$$(cat $(TOKEN_FILE)); \
	RESULT=$$(docker exec airflow-api-server sh -c \
		"curl -s -X 'POST' \
		'http://localhost:8080/api/v2/connections' \
		-H 'accept: application/json' \
		-H 'Content-Type: application/json' \
		-H 'Authorization: Bearer $$TOKEN' \
		-d '{ \
			\"connection_id\": \"inlabs_portal\", \
			\"conn_type\": \"http\", \
			\"description\": \"Credencial para acesso no Portal do INLabs\", \
			\"host\": \"https://inlabs.in.gov.br/\", \
			\"login\": \"user@email.com\", \
			\"password\": \"password\" \
		}'"); \
	echo "$$RESULT" | grep -q "Unique constraint violation" && echo "Connection already exists (Unique constraint violation)." || echo "$$RESULT"

create-opensearch-variable: get_access_token
	@echo "Creating 'opensearch' Airflow variables"
	@TOKEN=$$(cat $(TOKEN_FILE)); \
	RESULT=$$(docker exec airflow-api-server sh -c \
		"curl -s -X 'POST' \
		'http://localhost:8080/api/v2/variables' \
		-H 'accept: application/json' \
		-H 'Content-Type: application/json' \
		-H 'Authorization: Bearer $$TOKEN' \
		-d '{ \
		\"key\": \"RO_DOU_INLABS_USE_OPENSEARCH\", \
		\"value\": \"False\" \
		}'"); \
	echo "$$RESULT" | grep -q "The Variable with key: \`RO_DOU_INLABS_USE_OPENSEARCH\` already exists" && echo "The Variable with key: RO_DOU_INLABS_USE_OPENSEARCH already exists" || echo "$$RESULT"; \
	RESULT=$$(docker exec airflow-api-server sh -c \
		"curl -s -X 'POST' \
		'http://localhost:8080/api/v2/variables' \
		-H 'accept: application/json' \
		-H 'Content-Type: application/json' \
		-H 'Authorization: Bearer $$TOKEN' \
		-d '{ \
		\"key\": \"OPENSEARCH_HOST\", \
		\"value\": \"http://opensearch:9200\" \
		}'"); \
	echo "$$RESULT" | grep -q "The Variable with key: \`OPENSEARCH_HOST\` already exists" && echo "The Variable with key: OPENSEARCH_HOST already exists" || echo "$$RESULT"; \
	RESULT=$$(docker exec airflow-api-server sh -c \
		"curl -s -X 'POST' \
		'http://localhost:8080/api/v2/variables' \
		-H 'accept: application/json' \
		-H 'Content-Type: application/json' \
		-H 'Authorization: Bearer $$TOKEN' \
		-d '{ \
		\"key\": \"OPENSEARCH_USER\", \
		\"value\": \"OPENSEARCH_USER\" \
		}'"); \
	echo "$$RESULT" | grep -q "The Variable with key: \`OPENSEARCH_USER\` already exists" && echo "The Variable with key: OPENSEARCH_USER already exists" || echo "$$RESULT"; \
	RESULT=$$(docker exec airflow-api-server sh -c \
		"curl -s -X 'POST' \
		'http://localhost:8080/api/v2/variables' \
		-H 'accept: application/json' \
		-H 'Content-Type: application/json' \
		-H 'Authorization: Bearer $$TOKEN' \
		-d '{ \
		\"key\": \"OPENSEARCH_PASS\", \
		\"value\": \"OPENSEARCH_PASS\" \
		}'"); \
	echo "$$RESULT" | grep -q "The Variable with key: \`OPENSEARCH_PASS\` already exists" && echo "The Variable with key: OPENSEARCH_PASS already exists" || echo "$$RESULT"

activate-inlabs-load-dag: get_access_token
	@echo "Activating 'dou_inlabs_load_pg' Airflow DAG"
	@TOKEN=$$(cat $(TOKEN_FILE)); \
	RESULT=$$(docker exec airflow-api-server sh -c \
		"curl -s -X 'PATCH' \
		'http://localhost:8080/api/v2/dags/ro-dou_inlabs_load_pg' \
		-H 'accept: application/json' \
		-H 'Content-Type: application/json' \
		-H 'Authorization: Bearer $$TOKEN' \
		-d '{ \
		\"is_paused\": false \
		}'"); \
	echo "$$RESULT" | grep -qE '"is_paused"[[:space:]]*:[[:space:]]*false' && echo "DAG 'ro-dou_inlabs_load_pg' activated (is_paused: false)." || echo "$$RESULT"

create-azure-openai-endpoint-variable:get_access_token
	@echo "Creating 'AZURE_OPENAI_ENDPOINT' Airflow variable"
	@TOKEN=$$(cat $(TOKEN_FILE)); \
	RESULT=$$(docker exec airflow-api-server sh -c \
		"curl -s -X 'POST' \
			'http://localhost:8080/api/v2/variables' \
			-H 'accept: application/json' \
			-H 'Content-Type: application/json' \
			-H 'Authorization: Bearer $$TOKEN' \
		-d '{ \
		\"key\": \"AZURE_OPENAI_ENDPOINT\", \
		\"value\": \"https://sumarizacao-de-textos.services.ai.azure.com/\" \
		}'"); \
	echo "$$RESULT" | grep -q "The Variable with key: \`AZURE_OPENAI_ENDPOINT\` already exists" && echo "The Variable with key: AZURE_OPENAI_ENDPOINT already exists" || echo "$$RESULT"

create-azure-openai-api-version-variable:get_access_token
	@echo "Creating 'AZURE_OPENAI_API_VERSION' Airflow variable"
	@TOKEN=$$(cat $(TOKEN_FILE)); \
	RESULT=$$(docker exec airflow-api-server sh -c \
		"curl -s -X 'POST' \
		'http://localhost:8080/api/v2/variables' \
		-H 'accept: application/json' \
		-H 'Content-Type: application/json' \
		-H 'Authorization: Bearer $$TOKEN' \
		-d '{ \
		\"key\": \"AZURE_OPENAI_API_VERSION\", \
		\"value\": \"2024-02-01\" \
		}'"); \
	echo "$$RESULT" | grep -q "The Variable with key: \`AZURE_OPENAI_API_VERSION\` already exists" && echo "The Variable with key: AZURE_OPENAI_API_VERSION already exists" || echo "$$RESULT"

create-azure-openai-deployment-variable:get_access_token
	@echo "Creating 'AZURE_OPENAI_DEPLOYMENT' Airflow variable"
	@TOKEN=$$(cat $(TOKEN_FILE)); \
	RESULT=$$(docker exec airflow-api-server sh -c \
		"curl -s -X 'POST' \
		'http://localhost:8080/api/v2/variables' \
		-H 'accept: application/json' \
		-H 'Content-Type: application/json' \
		-H 'Authorization: Bearer $$TOKEN' \
		-d '{ \
		\"key\": \"AZURE_OPENAI_DEPLOYMENT\", \
		\"value\": \"gpt-4o-mini\" \
		}'"); \
	echo "$$RESULT" | grep -q "The Variable with key: \`AZURE_OPENAI_DEPLOYMENT\` already exists" && echo "The Variable with key: AZURE_OPENAI_DEPLOYMENT already exists" || echo "$$RESULT"

create-azure-openai-api-key-variable:get_access_token
	@echo "Creating 'AZURE_OPENAI_API_KEY' Airflow variable"
	@TOKEN=$$(cat $(TOKEN_FILE)); \
	RESULT=$$(docker exec airflow-api-server sh -c \
		"curl -s -X 'POST' \
		'http://localhost:8080/api/v2/variables' \
		-H 'accept: application/json' \
		-H 'Content-Type: application/json' \
		-H 'Authorization: Bearer $$TOKEN' \
		-d '{ \
		\"key\": \"AZURE_OPENAI_API_KEY\", \
		\"value\": \"<your-api-key>\" \
		}'"); \
	echo "$$RESULT" | grep -q "The Variable with key: \`AZURE_OPENAI_API_KEY\` already exists" && echo "The Variable with key: AZURE_OPENAI_API_KEY already exists" || echo "$$RESULT";

delete_token:
	@echo "Deleting token file"
	@rm -f $(TOKEN_FILE)
.PHONY: down
down:
	docker compose down

.PHONY: tests
tests:
	docker exec airflow-api-server sh -c "cd /opt/airflow/tests/ && pytest -vvv --color=yes"

#PYTHONWARNINGS=ignore evita deprecation warnings do próprio Airflow poluindo o terminal interativo.
.PHONY: gerar-yml
gerar-yml:
	@docker inspect -f '{{.State.Running}}' airflow-api-server >/dev/null 2>&1 || { \
		echo "Erro: o container airflow-api-server não está rodando."; \
		echo "Suba o ambiente primeiro com: make run"; \
		exit 1; \
	}
	docker exec -it -e PYTHONWARNINGS=ignore airflow-api-server python3 /opt/airflow/tools/gerador_cli.py
