"""Doctest collection (``pytest --doctest-modules pyeyesweb``).

The docstring examples run features backed by the compiled core. Without the core the package cannot be imported, so
its modules are not collected; the same ``EYESWEB_CORE_PATH`` as in ``tests/conftest.py`` locates the core.
"""

import os
import sys

if os.environ.get("EYESWEB_CORE_PATH"):
    sys.path.insert(0, os.environ["EYESWEB_CORE_PATH"])

try:
    import pyeyesweb._core  # noqa: F401
except ImportError:
    collect_ignore_glob = ["pyeyesweb/*"]
