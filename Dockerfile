FROM apache/airflow:2.10.0-python3.10

USER root

# Copy Ro-dou core files from the host Docker context
COPY src /opt/airflow/dags/ro_dou_src
COPY dag_confs/examples_and_tests /opt/airflow/dags/ro_dou/dag_confs
COPY dag_load_inlabs /opt/airflow/dags/ro_dou/dag_load_inlabs

RUN chown -R airflow /opt/airflow

# Install additional Airflow dependencies
USER airflow

COPY requirements-uninstall.txt .
RUN pip uninstall -y -r requirements-uninstall.txt && \
  pip install --no-cache-dir \
  apache-airflow-providers-microsoft-mssql==3.9.0 \
  apache-airflow-providers-common-sql==1.16.0

# Copy and install MAIN requirements.txt
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy and install requirements.txt
COPY tests-requirements.txt .
RUN pip install --no-cache-dir -r tests-requirements.txt