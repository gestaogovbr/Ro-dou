.PHONY: run
run: setup-containers create-example-variable

setup-containers:
	docker-compose up -d --force-recreate --remove-orphans

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

.PHONY: down
down:
	docker-compose down

.PHONY: tests
tests:
	docker exec airflow-webserver sh -c "cd /opt/airflow/tests/ && pytest -vvv --color=yes"
