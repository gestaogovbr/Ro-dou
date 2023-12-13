FROM apache/airflow:2.7.3-python3.10

USER root
RUN apt-get update \
&& apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev

# Copy Ro-dou core files from the host Docker context
COPY src /opt/airflow/dags/ro_dou

RUN chown -R airflow /opt/airflow


# Install additional Airflow dependencies
USER airflow

RUN pip install --no-cache-dir --user \
apache-airflow[microsoft.mssql,google_auth]

# Copy and install requirements.txt
COPY tests-requirements.txt /
RUN pip install --no-cache-dir -r /tests-requirements.txt
