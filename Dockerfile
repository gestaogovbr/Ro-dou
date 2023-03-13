FROM apache/airflow:2.5.1

RUN pip install --no-cache-dir --user 'apache-airflow[microsoft.mssql,google_auth]'
COPY requirements.txt /
RUN pip install --no-cache-dir -r /requirements.txt
