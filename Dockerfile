FROM apache/airflow:3.3.0-python3.11

USER root

# Copy Ro-dou core files from the host Docker context
COPY src /opt/airflow/dags/ro_dou_src
COPY dag_confs/examples_and_tests /opt/airflow/dags/ro_dou/dag_confs
COPY dag_load_inlabs /opt/airflow/dags/ro_dou/dag_load_inlabs

RUN chown -R airflow /opt/airflow

# Install additional Airflow dependencies
USER airflow

COPY requirements-uninstall.txt .
RUN pip install --upgrade pip && \
  pip uninstall -y -r requirements-uninstall.txt && \
  pip install --no-cache-dir \
  --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-3.3.0/constraints-3.11.txt" \
  apache-airflow-providers-microsoft-mssql \
  apache-airflow-providers-common-sql

# Copy and install requirements.txt
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
  --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-3.3.0/constraints-3.11.txt"

ARG AI_PROVIDERS=""

COPY requirements-ai.txt .

RUN if [ -n "$AI_PROVIDERS" ]; then \
  for provider in $AI_PROVIDERS; do \
      grep "# $provider" requirements-ai.txt | cut -d'#' -f1 >> /tmp/filtered.txt; \
  done && \
  pip install --no-cache-dir -r /tmp/filtered.txt \
  --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-3.3.0/constraints-3.11.txt"; \
  fi


