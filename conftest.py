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


def pytest_collection_modifyitems(config, items):
    """The examples of ``pyeyesweb.datasets`` read the example recordings: skip them where there is no copy."""
    import pytest

    try:
        from pyeyesweb import datasets
        missing = not datasets.available_trials() or not (datasets._checkout_data_dir() / "qualisys").is_dir()
    except ImportError:
        return
    if missing:
        skip = pytest.mark.skip(reason="example data not available")
        for item in items:
            if item.nodeid.startswith("pyeyesweb/datasets.py"):
                item.add_marker(skip)
