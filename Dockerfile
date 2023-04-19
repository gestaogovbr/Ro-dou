FROM apache/airflow:2.5.0-python3.9

USER root

# Copy Ro-dou core files from the host Docker context
COPY src /opt/airflow/dags/ro_dou

USER airflow

# Install additional Airflow dependencies
RUN pip install --no-cache-dir --user \
    apache-airflow[microsoft.mssql,google_auth] \
    apache-airflow-providers-fastetl

# Copy and install requirements.txt
COPY requirements.txt /
RUN pip install --no-cache-dir -r /requirements.txt
