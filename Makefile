include .env
export $(shell sed 's/=.*//' .env)

# Detect docker compose command (docker-compose or "docker compose")
COMPOSE := $(shell command -v docker-compose >/dev/null 2>&1 && echo docker-compose || echo docker compose)

# Nome do projeto Docker Compose. Primeiro respeita a variável de ambiente
# COMPOSE_PROJECT_NAME (se definida). Caso contrário, usa o nome padrão 'ro-dou'.
# Usa condicionais make para garantir que PROJECT nunca fique vazio.
PROJECT ?= $(if $(COMPOSE_PROJECT_NAME),$(COMPOSE_PROJECT_NAME),ro-dou)

# Timeout (seconds) for wait-web loop; can be overridden in environment
WAIT_WEB_TIMEOUT ?= 60

# Profile usado para serviços opcionais de desenvolvimento (ex.: smtp4dev)
# Defina DEV_PROFILE= (vazio) para desabilitar por padrão
DEV_PROFILE ?= dev
DEV_PROFILE_ARG := $(if $(DEV_PROFILE),--profile $(DEV_PROFILE),)

# Ensure docker is installed early
ifeq (, $(shell command -v docker)) 
$(error "docker não encontrado. Instale o Docker e tente novamente.")
endif
include .env
export $(shell sed 's/=.*//' .env)

# Detect docker compose command (docker-compose or "docker compose")
COMPOSE := $(shell command -v docker-compose >/dev/null 2>&1 && echo docker-compose || echo docker compose)

# Nome do projeto Docker Compose. Primeiro respeita a variável de ambiente
# COMPOSE_PROJECT_NAME (se definida). Caso contrário, usa o nome padrão 'ro-dou'.
# Usa condicionais make para garantir que PROJECT nunca fique vazio.
PROJECT ?= $(if $(COMPOSE_PROJECT_NAME),$(COMPOSE_PROJECT_NAME),ro-dou)

# Timeout (seconds) for wait-web loop; can be overridden in environment
WAIT_WEB_TIMEOUT ?= 60

# Ensure docker is installed early
ifeq (, $(shell command -v docker))
$(error "docker não encontrado. Instale o Docker e tente novamente.")
endif

# Automatically choose Postgres data volume strategy:
# - If running under WSL with repo mounted under /mnt (Windows), default to a named volume
#   to avoid NTFS permission issues (chown/chmod failing on host bind mounts).
# - Otherwise, use the host path ./mnt/pgdata as before.
ifdef WSL_DISTRO_NAME
POSTGRES_DATA_VOLUME ?= rodou_pgdata
else
POSTGRES_DATA_VOLUME ?= ./mnt/pgdata
endif
export POSTGRES_DATA_VOLUME

.PHONY: help
help:
	@echo "Usage: make <target>"
	@echo "Common targets: run build-images redeploy down tests smoke-test wait-web"

.PHONY: run
run: \
	build-images \
	create-logs-dir \
	setup-containers \
	wait-web \
	create-example-variable \
	create-path-tmp-variable \
	create-inlabs-db \
	create-inlabs-db-connection \
	create-inlabs-portal-connection \
	activate-inlabs-load-dag

.PHONY: build-images
build-images:
	$(COMPOSE) $(DEV_PROFILE_ARG) -p $(PROJECT) build airflow-webserver airflow-scheduler

create-logs-dir:
	mkdir -p ./mnt/airflow-logs -m a=rwx

setup-containers:
	$(COMPOSE) $(DEV_PROFILE_ARG) -p $(PROJECT) up -d

create-example-variable:
	@echo "Creating 'termos_exemplo_variavel' Airflow variable"
	@$(COMPOSE) $(DEV_PROFILE_ARG) -p $(PROJECT) exec -T airflow-webserver sh -c \
		"curl -f -s -LI 'http://localhost:8080/api/v1/variables/termos_exemplo_variavel' --user '$(AIRFLOW_USER):$(AIRFLOW_PASSWORD)' >/dev/null \
		|| curl -s -X POST 'http://localhost:8080/api/v1/variables' \
			-H 'accept: application/json' -H 'Content-Type: application/json' \
			--user '$(AIRFLOW_USER):$(AIRFLOW_PASSWORD)' \
			-d '{\"key\":\"termos_exemplo_variavel\",\"value\":\"LGPD\\nlei geral de proteção de dados\\nacesso à informação\"}' >/dev/null"

create-path-tmp-variable:
	@echo "Creating 'path_tmp' Airflow variable"
	@$(COMPOSE) $(DEV_PROFILE_ARG) -p $(PROJECT) exec -T airflow-webserver sh -c \
		"if ! curl -f -s -LI 'http://localhost:8080/api/v1/variables/path_tmp' --user \"$(AIRFLOW_USER):$(AIRFLOW_PASSWORD)\" > /dev/null; \
		then \
			curl -s -X 'POST' \
			'http://localhost:8080/api/v1/variables' \
			-H 'accept: application/json' \
			-H 'Content-Type: application/json' \
			--user \"$(AIRFLOW_USER):$(AIRFLOW_PASSWORD)\" \
			--user \"$(AIRFLOW_USER):$(AIRFLOW_PASSWORD)\" \
			-d '{ \
			"key": "path_tmp", \
			"value": "$(AIRFLOW_TMP_DIR)" \
			}' > /dev/null; \
		fi"

create-inlabs-db:
	@echo "Creating 'inlabs' database"
	@$(COMPOSE) $(DEV_PROFILE_ARG) -p $(PROJECT) exec -T -e PGPASSWORD=$(POSTGRES_PASSWORD) postgres \
		psql --username=$(POSTGRES_USER) --dbname=$(POSTGRES_DB) --file=/sql/init-db.sql > /dev/null

create-inlabs-db-connection:
	@echo "Creating 'inlabs_db' Airflow connection"
	@$(COMPOSE) $(DEV_PROFILE_ARG) -p $(PROJECT) exec -T airflow-webserver sh -c \
		"if ! curl -f -s -LI 'http://localhost:8080/api/v1/connections/inlabs_db' --user \"$(AIRFLOW_USER):$(AIRFLOW_PASSWORD)\" > /dev/null; \
		then \
			curl -s -X 'POST' \
			'http://localhost:8080/api/v1/connections' \
			-H 'accept: application/json' \
			-H 'Content-Type: application/json' \
			--user \"$(AIRFLOW_USER):$(AIRFLOW_PASSWORD)\" \
			--user \"$(AIRFLOW_USER):$(AIRFLOW_PASSWORD)\" \
			-d '{ \
			"connection_id": "inlabs_db", \
			"conn_type": "postgres", \
			"schema": "inlabs", \
			"host": "$(POSTGRES_HOST)", \
			"login": "$(POSTGRES_USER)", \
			"password": "$(POSTGRES_PASSWORD)", \
			"port": $(POSTGRES_PORT) \
			}' > /dev/null; \
		fi"

create-inlabs-portal-connection:
	@echo "Force Creating 'inlabs_portal' Airflow connection"
	@$(COMPOSE) $(DEV_PROFILE_ARG) -p $(PROJECT) exec -T airflow-webserver airflow connections delete inlabs_portal || true
	@$(COMPOSE) $(DEV_PROFILE_ARG) -p $(PROJECT) exec -T airflow-webserver airflow connections add inlabs_portal \
		--conn-type http \
		--conn-host "$(INLABS_PORTAL_HOST)" \
		--conn-login "$(INLABS_PORTAL_LOGIN)" \
		--conn-password "$(INLABS_PORTAL_PASSWORD)" \
		--conn-description "Credencial para acesso no Portal do INLabs"

activate-inlabs-load-dag:
	@echo "Activating 'ro-dou_inlabs_load_pg' Airflow DAG"
	@$(COMPOSE) $(DEV_PROFILE_ARG) -p $(PROJECT) exec -T airflow-webserver sh -c \
		"curl -s -X 'PATCH' \
			'http://localhost:8080/api/v1/dags/ro-dou_inlabs_load_pg' \
			-H 'accept: application/json' \
			-H 'Content-Type: application/json' \
			--user \"$(AIRFLOW_USER):$(AIRFLOW_PASSWORD)\" \
			--user \"$(AIRFLOW_USER):$(AIRFLOW_PASSWORD)\" \
			-d '{ \
			"is_paused": false \
			}' > /dev/null;"
.PHONY: redeploy
redeploy: build-images
	docker compose -p ro-dou up -d --no-deps airflow-webserver airflow-scheduler
	$(MAKE) smoke-test

.PHONY: redeploy


redeploy: build-images
	$(COMPOSE) $(DEV_PROFILE_ARG) -p $(PROJECT) up -d --no-deps airflow-webserver airflow-scheduler
	$(MAKE) smoke-test

.PHONY: tests
tests:
	# Ensure the project code mounted at /opt/airflow/dags is on PYTHONPATH so
	# imports like `dags.ro_dou_src` resolve when pytest changes CWD to /opt/airflow/tests
	# Include both /opt/airflow/dags and /opt/airflow/dags/dags to handle
	# layouts where a nested `dags` package exists (common when src contains a
	# `dags/` directory). This makes imports like `dags.ro_dou_src` resilient.
	$(COMPOSE) $(DEV_PROFILE_ARG) -p $(PROJECT) exec -T airflow-webserver sh -c "cd /opt/airflow/tests/ && PYTHONPATH=/opt/airflow/dags:/opt/airflow/dags/dags python -m pytest -vvv --color=yes"

.PHONY: smoke-test
smoke-test:
	@$(COMPOSE) $(DEV_PROFILE_ARG) -p $(PROJECT) exec -T airflow-webserver bash -lc "python -c 'import requests; print(\"webserver https://www.in.gov.br ->\", requests.get(\"https://www.in.gov.br\", timeout=10).status_code)'"
	@$(COMPOSE) $(DEV_PROFILE_ARG) -p $(PROJECT) exec -T airflow-scheduler bash -lc "python -c 'import requests; print(\"scheduler https://www.in.gov.br ->\", requests.get(\"https://www.in.gov.br\", timeout=10).status_code)'"

.PHONY: wait-web
wait-web:
	@echo "Waiting for airflow-webserver (health=healthy) ..."
	@for i in $$(seq 1 $(WAIT_WEB_TIMEOUT)); do \
	state=$$(docker inspect --format='{{.State.Health.Status}}' airflow-webserver 2>/dev/null || echo "starting"); \
	if [ "$$state" = "healthy" ]; then echo "airflow-webserver is healthy"; exit 0; fi; \
	sleep 3; \
	done; \
	echo "Timeout waiting for airflow-webserver health=healthy"; exit 1

.PHONY: dev-up dev-down smtp4dev-up smtp4dev-down smtp4dev-stop smtp4dev-rm

dev-up:
	$(COMPOSE) $(DEV_PROFILE_ARG) -p $(PROJECT) up -d

dev-down:
	$(COMPOSE) $(DEV_PROFILE_ARG) -p $(PROJECT) down

# Start only the smtp4dev service (profile controlled by DEV_PROFILE)
smtp4dev-up:
	$(COMPOSE) $(DEV_PROFILE_ARG) -p $(PROJECT) up -d smtp4dev

# Stop and remove the smtp4dev service
smtp4dev-down: smtp4dev-stop smtp4dev-rm

smtp4dev-stop:
	$(COMPOSE) $(DEV_PROFILE_ARG) -p $(PROJECT) stop smtp4dev || true

smtp4dev-rm:
	$(COMPOSE) $(DEV_PROFILE_ARG) -p $(PROJECT) rm -f smtp4dev || true

.PHONY: down
down:
	$(COMPOSE) $(DEV_PROFILE_ARG) -p $(PROJECT) down

.PHONY: smoke-test
smoke-test:
	@docker exec airflow-webserver bash -lc "python -c 'import requests; print(\"webserver https://www.in.gov.br ->\", requests.get(\"https://www.in.gov.br\", timeout=10).status_code)'"
	@docker exec airflow-scheduler bash -lc "python -c 'import requests; print(\"scheduler https://www.in.gov.br ->\", requests.get(\"https://www.in.gov.br\", timeout=10).status_code)'"

.PHONY: wait-web
wait-web:
	@echo "Waiting for airflow-webserver (health=healthy) ..."
	@for i in $$(seq 1 60); do \
	  state=$$(docker inspect --format='{{.State.Health.Status}}' airflow-webserver 2>/dev/null || echo "starting"); \
	  if [ "$$state" = "healthy" ]; then echo "airflow-webserver is healthy"; exit 0; fi; \
	  sleep 3; \
	done; \
	echo "Timeout waiting for airflow-webserver health=healthy"; exit 1