FROM apache/airflow:3.3.0-python3.11

USER root

# Copy Ro-dou core files from the host Docker context
COPY src /opt/airflow/dags/ro_dou_src
COPY dag_confs/examples_and_tests /opt/airflow/dags/ro_dou/dag_confs
COPY dag_load_inlabs /opt/airflow/dags/ro_dou/dag_load_inlabs
# Tela de gestão de DAGs (plugin) e o formulário compartilhado com a documentação
COPY plugins /opt/airflow/plugins
COPY docs/docs/gerador_yaml.html /opt/airflow/ro_dou_docs/gerador_yaml.html

RUN chown -R airflow /opt/airflow

# Ensure the dags and ro_dou_src packages are importable in container Python
ENV PYTHONPATH="/opt/airflow/dags:/opt/airflow:$PYTHONPATH"

# Install additional Airflow dependencies
USER airflow

COPY requirements-uninstall.txt .
RUN uv pip uninstall -r requirements-uninstall.txt && \
  uv pip install --no-cache \
  apache-airflow-providers-microsoft-mssql==4.7.0 \
  apache-airflow-providers-common-sql==2.0.3

# Copy and install requirements.txt
COPY requirements.txt .
RUN uv pip install --no-cache -r requirements.txt

ARG AI_PROVIDERS=""

COPY requirements-ai.txt .

RUN uv pip install --no-cache -r requirements-ai.txt
