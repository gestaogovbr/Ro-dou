import json
import jsonschema
import pytest
import glob
import yaml
import requests
from urllib.parse import urlparse


YAMLS_DIR = "../dags/ro_dou/dag_confs"
SCHEMA_FILEPATH = "../schemas/ro-dou.json"
# or
# SCHEMA_FILEPATH = "https://raw.githubusercontent.com/gestaogovbr/Ro-dou/main/schemas/ro-dou.json"


def get_schema(filepath):
    def _is_valid_url(url):
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except ValueError:
            return False

    if _is_valid_url(filepath):
        response = requests.get(filepath)
        response.raise_for_status()
        return json.loads(response.text)
    else:
        with open(filepath) as f:
            return json.load(f)


SCHEMA = get_schema(SCHEMA_FILEPATH)

@pytest.mark.parametrize(
    "data_file",
    [
        data_file
        for data_file in glob.glob(f"{YAMLS_DIR}/**/*.yml", recursive=True)
        + glob.glob(f"{YAMLS_DIR}/**/*.yaml", recursive=True)
    ],
)
def test_json_schema_validation(data_file):
    with open(data_file) as data_fp:
        data = yaml.safe_load(data_fp)

    jsonschema.validate(instance=data, schema=SCHEMA)
