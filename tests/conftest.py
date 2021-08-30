import os
from airflow import models
from airflow.utils import db

TEST_AIRFLOW_HOME = '/opt/airflow'

# TEST_AIRFLOW_HOME = os.path.join(
#     os.path.dirname(__file__),
#     'test_airflow_home',
# )
TEST_ENV_VARS = {
    'AIRFLOW_HOME': TEST_AIRFLOW_HOME
}

APP_NAME = 'pytest-airflow-dou_dag_generator'


def pytest_configure(config):
    """Configure and init envvars for airflow."""
    config.old_env = {}
    for key, value in TEST_ENV_VARS.items():
        config.old_env[key] = os.getenv(key)
        os.environ[key] = value

def pytest_unconfigure(config):
    """Restore envvars to old values."""
    for key, value in config.old_env.items():
        if value is None:
            del os.environ[key]
        else:
            os.environ[key] = value
