FROM apache/airflow:2.6.3-python3.10

USER root

# Copy Ro-dou core files from the host Docker context
COPY src /opt/airflow/dags/ro_dou

# Install Git
RUN apt-get update && \
    apt-get install -y git && \
    rm -rf /var/lib/apt/lists/*

# Clone the FastETL GitHub repository and copy specified files
RUN git clone https://github.com/gestaogovbr/FastETL.git /tmp/repo-FastETL && \
    mkdir -p /opt/airflow/plugins/fastetl/hooks && \
    mkdir -p /opt/airflow/plugins/fastetl/custom_functions/utils && \
    cp /tmp/repo-FastETL/fastetl/hooks/dou_hook.py /opt/airflow/plugins/fastetl/hooks/ && \
    cp -r /tmp/repo-FastETL/fastetl/custom_functions/utils/date.py /opt/airflow/plugins/fastetl/custom_functions/utils/

# Remove Git and clean up package cache
RUN apt-get remove -y git && \
    apt-get autoremove -yqq --purge && \
    apt-get clean && \
    rm -rf /tmp/repo-FastETL

RUN chown -R airflow /opt/airflow

USER airflow

# Install additional Airflow dependencies
RUN pip install --no-cache-dir --user 'apache-airflow[microsoft.mssql,google_auth]'

# Copy and install requirements.txt
COPY tests-requirements.txt /
RUN pip install --no-cache-dir -r /tests-requirements.txt
