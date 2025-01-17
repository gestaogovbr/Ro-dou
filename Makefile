.PHONY: run
run: \
create-logs-dir \
setup-containers \
create-example-variable \
create-path-tmp-variable \
create-inlabs-db \
create-inlabs-db-connection \
create-inlabs-portal-connection \
activate-inlabs-load-dag

create-logs-dir:
	mkdir -p ./mnt/airflow-logs -m a=rwx

setup-containers:
	docker compose up -d --force-recreate --remove-orphans

create-example-variable:
	@echo 'Waiting for Airflow API to start ...'
	@docker exec airflow-webserver sh -c "while ! curl -f -s -LI 'http://localhost:8080/' > /dev/null; do sleep 5; done;"
	@echo "Creating 'termos_exemplo_variavel' Airflow variable"
	@docker exec airflow-webserver sh -c \
		"if ! curl -f -s -LI 'http://localhost:8080/api/v1/variables/termos_exemplo_variavel' --user \"airflow:airflow\" > /dev/null; \
		then \
			curl -s -X 'POST' \
			'http://localhost:8080/api/v1/variables' \
			-H 'accept: application/json' \
			-H 'Content-Type: application/json' \
			--user \"airflow:airflow\" \
			-d '{ \
			\"key\": \"termos_exemplo_variavel\", \
			\"value\": \"LGPD\nlei geral de proteção de dados\nacesso à informação\" \
			}' > /dev/null; \
		fi"

create-path-tmp-variable:
	@echo "Creating 'path_tmp' Airflow variable"
	@docker exec airflow-webserver sh -c \
		"if ! curl -f -s -LI 'http://localhost:8080/api/v1/variables/path_tmp' --user \"airflow:airflow\" > /dev/null; \
		then \
			curl -s -X 'POST' \
			'http://localhost:8080/api/v1/variables' \
			-H 'accept: application/json' \
			-H 'Content-Type: application/json' \
			--user \"airflow:airflow\" \
			-d '{ \
			\"key\": \"path_tmp\", \
			\"value\": \"/tmp\" \
			}' > /dev/null; \
		fi"

create-inlabs-db:
	@echo "Creating 'inlabs' database"
	@docker exec -e PGPASSWORD=airflow ro-dou-postgres-1 sh -c "psql -q -U airflow -f /sql/init-db.sql > /dev/null"

create-inlabs-db-connection:
	@echo "Creating 'inlabs_db' Airflow connection"
	@docker exec airflow-webserver sh -c \
		"if ! curl -f -s -LI 'http://localhost:8080/api/v1/connections/inlabs_db' --user \"airflow:airflow\" > /dev/null; \
		then \
			curl -s -X 'POST' \
			'http://localhost:8080/api/v1/connections' \
			-H 'accept: application/json' \
			-H 'Content-Type: application/json' \
			--user \"airflow:airflow\" \
			-d '{ \
			\"connection_id\": \"inlabs_db\", \
			\"conn_type\": \"postgres\", \
			\"schema\": \"inlabs\", \
			\"host\": \"ro-dou-postgres-1\", \
			\"login\": \"airflow\", \
			\"password\": \"airflow\", \
			\"port\": 5432 \
			}' > /dev/null; \
		fi"

create-inlabs-portal-connection:
	@echo "Creating 'inlabs_portal' Airflow connection"
	@docker exec airflow-webserver sh -c \
		"if ! curl -f -s -LI 'http://localhost:8080/api/v1/connections/inlabs_portal' --user \"airflow:airflow\" > /dev/null; \
		then \
			curl -s -X 'POST' \
			'http://localhost:8080/api/v1/connections' \
			-H 'accept: application/json' \
			-H 'Content-Type: application/json' \
			--user \"airflow:airflow\" \
			-d '{ \
			\"connection_id\": \"inlabs_portal\", \
			\"conn_type\": \"http\", \
			\"description\": \"Credencial para acesso no Portal do INLabs\", \
			\"host\": \"https://inlabs.in.gov.br/\", \
			\"login\": \"user@email.com\", \
			\"password\": \"password\" \
			}' > /dev/null; \
		fi"

activate-inlabs-load-dag:
	@echo "Activating 'dou_inlabs_load_pg' Airflow DAG"
	@docker exec airflow-webserver sh -c \
		"curl -s -X 'PATCH' \
			'http://localhost:8080/api/v1/dags/ro-dou_inlabs_load_pg' \
			-H 'accept: application/json' \
			-H 'Content-Type: application/json' \
			--user \"airflow:airflow\" \
			-d '{ \
			\"is_paused\": false \
			}' > /dev/null;"

.PHONY: down
down:
	docker compose down

.PHONY: tests
tests:
	docker exec airflow-webserver sh -c "cd /opt/airflow/tests/ && pytest -vvv --color=yes"
