FROM apache/airflow:2.5.1

USER root

# Copy Ro-dou core files from the host Docker context
COPY src /opt/airflow/dags/ro_dou

# Install Git
RUN apt-get update && \
    apt-get install -y git && \
    rm -rf /var/lib/apt/lists/*

# Clone the FastETL GitHub repository and copy specified files
RUN git clone https://github.com/economiagovbr/FastETL.git /tmp/repo-FastETL && \
    mkdir -p /opt/airflow/plugins/FastETL/hooks && \
    mkdir -p /opt/airflow/plugins/FastETL/custom_functions/utils && \
    cp /tmp/repo-FastETL/hooks/dou_hook.py /opt/airflow/plugins/FastETL/hooks/dou_hook.py && \
    cp -r /tmp/repo-FastETL/custom_functions/utils/* /opt/airflow/plugins/FastETL/custom_functions/utils/

# Remove Git and clean up package cache
RUN apt-get remove -y git && \
    apt-get autoremove -y && \
    rm -rf /tmp/repo-ro-dou && \
    rm -rf /tmp/repo-FastETL

USER airflow

# Install additional Airflow dependencies
RUN pip install --no-cache-dir --user 'apache-airflow[microsoft.mssql,google_auth]'

# Copy and install requirements.txt
COPY requirements.txt /
RUN pip install --no-cache-dir -r /requirements.txt
