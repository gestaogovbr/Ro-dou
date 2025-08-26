"""Compatibility shim package to expose project code as `dags.ro_dou_src`.

Some tests and imports expect modules under the package `dags.ro_dou_src`.
The actual implementation lives in `src/` for development convenience. This
shim inserts the repository `src` directory into sys.path and re-exports the
package namespace so imports like `from dags.ro_dou_src import dou_dag_generator`
continue to work both in CI and in local container runs.
"""
import os
import sys

# Compute absolute path to the repo `src` directory
_HERE = os.path.abspath(os.path.dirname(__file__))
_SRC = os.path.abspath(os.path.join(_HERE, '..', '..', 'src'))
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

# Re-export package metadata if present
try:
    # Attempt to import common modules to fail fast if something is broken
    from dou_dag_generator import *  # noqa: F401,F403
except Exception:
    # Import errors will be surfaced when tests import specific names; silence
    # here to allow pytest to report the concrete failure with traceback.
    pass
