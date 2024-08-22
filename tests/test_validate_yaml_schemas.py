"""Test validation of yaml files according to the defined schemas.
"""

import glob
import os
import sys

from pydantic import ValidationError
import pytest
import yaml

# add module path so we can import from other modules
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
from schemas import RoDouConfig

YAMLS_DIR = "../dags/ro_dou/dag_confs"


@pytest.mark.parametrize(
    "data_file",
    [
        data_file
        for data_file in glob.glob(f"{YAMLS_DIR}/**/*.yml", recursive=True)
        + glob.glob(f"{YAMLS_DIR}/**/*.yaml", recursive=True)
    ],
)
def test_pydantic_validation(data_file):
    with open(data_file) as data_fp:
        data = yaml.safe_load(data_fp)

    try:
        RoDouConfig(**data)
    except ValidationError as e:
        pytest.fail(f"YAML file {data_file} is not valid:\n{e}")
