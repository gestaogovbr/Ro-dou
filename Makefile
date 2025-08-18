include .env
export $(shell sed 's/=.*//' .env)

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
	docker compose -p ro-dou build airflow-webserver airflow-scheduler

create-logs-dir:
	mkdir -p ./mnt/airflow-logs -m a=rwx

setup-containers:
	docker compose -p ro-dou up -d

create-example-variable:
	@echo "Creating 'termos_exemplo_variavel' Airflow variable"
	@docker exec airflow-webserver sh -c \
		"curl -f -s -LI 'http://localhost:8080/api/v1/variables/termos_exemplo_variavel' --user '$(AIRFLOW_USER):$(AIRFLOW_PASSWORD)' >/dev/null \
		|| curl -s -X POST 'http://localhost:8080/api/v1/variables' \
			-H 'accept: application/json' -H 'Content-Type: application/json' \
			--user '$(AIRFLOW_USER):$(AIRFLOW_PASSWORD)' \
			-d '{\"key\":\"termos_exemplo_variavel\",\"value\":\"LGPD\nlei geral de proteção de dados\nacesso à informação\"}' >/dev/null"


create-path-tmp-variable:
	@echo "Creating 'path_tmp' Airflow variable"
	@docker exec airflow-webserver sh -c \
		"if ! curl -f -s -LI 'http://localhost:8080/api/v1/variables/path_tmp' --user \"$(AIRFLOW_USER):$(AIRFLOW_PASSWORD)\" > /dev/null; \
		then \
			curl -s -X 'POST' \
			'http://localhost:8080/api/v1/variables' \
			-H 'accept: application/json' \
			-H 'Content-Type: application/json' \
			--user \"$(AIRFLOW_USER):$(AIRFLOW_PASSWORD)\" \
			-d '{ \
			\"key\": \"path_tmp\", \
			\"value\": \"$(AIRFLOW_TMP_DIR)\" \
			}' > /dev/null; \
		fi"

create-inlabs-db:
	@echo "Creating 'inlabs' database"
	@docker exec -e PGPASSWORD=$(POSTGRES_PASSWORD) ro-dou-postgres-1 \
		psql --username=$(POSTGRES_USER) --dbname=$(POSTGRES_DB) --file=/sql/init-db.sql > /dev/null

create-inlabs-db-connection:
	@echo "Creating 'inlabs_db' Airflow connection"
	@docker exec airflow-webserver sh -c \
		"if ! curl -f -s -LI 'http://localhost:8080/api/v1/connections/inlabs_db' --user \"$(AIRFLOW_USER):$(AIRFLOW_PASSWORD)\" > /dev/null; \
		then \
			curl -s -X 'POST' \
			'http://localhost:8080/api/v1/connections' \
			-H 'accept: application/json' \
			-H 'Content-Type: application/json' \
			--user \"$(AIRFLOW_USER):$(AIRFLOW_PASSWORD)\" \
			-d '{ \
			\"connection_id\": \"inlabs_db\", \
			\"conn_type\": \"postgres\", \
			\"schema\": \"inlabs\", \
			\"host\": \"$(POSTGRES_HOST)\", \
			\"login\": \"$(POSTGRES_USER)\", \
			\"password\": \"$(POSTGRES_PASSWORD)\", \
			\"port\": $(POSTGRES_PORT) \
			}' > /dev/null; \
		fi"

create-inlabs-portal-connection:
	@echo "Force Creating 'inlabs_portal' Airflow connection"
	@docker exec airflow-webserver airflow connections delete inlabs_portal || true
	@docker exec airflow-webserver airflow connections add inlabs_portal \
		--conn-type http \
		--conn-host "$(INLABS_PORTAL_HOST)" \
		--conn-login "$(INLABS_PORTAL_LOGIN)" \
		--conn-password "$(INLABS_PORTAL_PASSWORD)" \
		--conn-description "Credencial para acesso no Portal do INLabs"

activate-inlabs-load-dag:
	@echo "Activating 'ro-dou_inlabs_load_pg' Airflow DAG"
	@docker exec airflow-webserver sh -c \
		"curl -s -X 'PATCH' \
			'http://localhost:8080/api/v1/dags/ro-dou_inlabs_load_pg' \
			-H 'accept: application/json' \
			-H 'Content-Type: application/json' \
			--user \"$(AIRFLOW_USER):$(AIRFLOW_PASSWORD)\" \
			-d '{ \
			\"is_paused\": false \
			}' > /dev/null;"
.PHONY: redeploy
redeploy: build-images
	docker compose -p ro-dou up -d --no-deps airflow-webserver airflow-scheduler
	$(MAKE) smoke-test

.PHONY: down
down:
	docker compose -p ro-dou down

.PHONY: tests
tests:
	@docker exec airflow-webserver sh -c "while ! curl -f -s -LI 'http://localhost:8080/' > /dev/null; do sleep 5; done;"
	docker exec airflow-webserver sh -c "cd /opt/airflow/tests/ && pytest -vvv --color=yes"

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