FROM apache/airflow:2.8.1-python3.10

USER root

# Copy Ro-dou core files from the host Docker context
COPY src /opt/airflow/dags/ro_dou_src

RUN chown -R airflow /opt/airflow


# Install additional Airflow dependencies
USER airflow

RUN pip install --no-cache-dir --user \
apache-airflow[microsoft.mssql,google_auth]

# Copy and install requirements.txt
COPY tests-requirements.txt /
RUN pip install --no-cache-dir -r /tests-requirements.txt
