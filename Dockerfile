FROM apache/airflow:2.10.0-python3.10

USER root

# Copy Ro-dou core files from the host Docker context
COPY src /opt/airflow/dags/ro_dou_src

RUN chown -R airflow /opt/airflow


# Install additional Airflow dependencies
USER airflow

COPY requirements-uninstall.txt .
RUN pip uninstall -y -r requirements-uninstall.txt && \
  pip install --no-cache-dir \
  apache-airflow-providers-microsoft-mssql==3.9.0 \
  apache-airflow-providers-common-sql==1.16.0

# Copy and install requirements.txt
COPY tests-requirements.txt .
RUN pip install --no-cache-dir -r tests-requirements.txt