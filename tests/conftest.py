"""Makes the compiled EyesWeb core (a development build) and the reference implementations importable for every test.

EYESWEB_CORE_PATH: directory holding `eyesweb_core*.pyd` (the CMake build output of the private EyesWebCore repository: `EyesWebCore/build/Release`). It is put on `sys.path` before any
test module is collected, so tests need no path handling of their own. The core is optional: tests that need it skip.
"""

import os
import sys

if os.environ.get("EYESWEB_CORE_PATH"):
    sys.path.insert(0, os.environ["EYESWEB_CORE_PATH"])
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "reference"))
sys.path.insert(0, os.path.dirname(__file__))  # contract_suite

# The features are backed by the compiled core, so without it only the tests of the pure-Python data model can run.
try:
    import pyeyesweb._core  # noqa: F401
except ImportError:
    _PURE = ("test_sliding_window.py", "test_output_contract.py")

    def pytest_ignore_collect(collection_path, config):
        name = collection_path.name
        return name.startswith("test_") and name not in _PURE
