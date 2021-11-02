.PHONY: install-deps
install-deps:
	git clone git@github.com:economiagovbr/FastETL.git

.PHONY: setup
setup:
	docker-compose up -d --force-recreate --remove-orphans

.PHONY: down
down:
	docker-compose down

.PHONY: tests
tests:
	docker exec airflow-webserver sh -c "cd /opt/airflow/tests/ && pytest -vvv"
