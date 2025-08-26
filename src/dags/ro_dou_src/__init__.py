"""Shim package to provide `dags.ro_dou_src` package when `src/` is mounted
into Airflow's DAGs directory. This makes `from dags.ro_dou_src import ...`
work without moving files.
"""
from __future__ import annotations

import os
import sys

# Ensure project root `src` is on sys.path (when this package is mounted at
# /opt/airflow/dags, the parent dir is /opt/airflow and project code lives in
# /opt/airflow/dags/.. -> the repo root). We make a best-effort to add the
# repository's `src` directory to the import path.
_HERE = os.path.abspath(os.path.dirname(__file__))
_REPO_ROOT = os.path.abspath(os.path.join(_HERE, '..', '..'))
_SRC = os.path.join(_REPO_ROOT, 'src')
if os.path.isdir(_SRC) and _SRC not in sys.path:
    sys.path.insert(0, _SRC)

# Re-export common modules for convenience
try:
    from dou_dag_generator import *  # noqa: F401,F403
except Exception:
    # Let imports fail later with helpful tracebacks in pytest
    pass
