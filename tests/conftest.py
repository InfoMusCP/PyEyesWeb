"""Makes the compiled EyesWeb core (a development build) and the shared test helpers
importable for every test.

Layout of `tests/`:
- `unit_tests/`: the tests. `test_parity_*.py` compare a feature with frozen data or check its input rules;
  `test_contract_*.py` run the shared contract check on features; `test_live_parameters*.py` check which parameters
  can change between calls; the rest test one feature or one rule.
- `_support/`: helpers, not tests. `contract_suite.py` (`check_feature_contract`: schema, statuses, `run` against
  `process`, reset), `live_param_suite.py` (live and structural parameter checks), and the input builders
  `humanoid_inputs.py`, `imaging_inputs.py`, `symmetry_inputs.py`.
- `data/`: frozen outputs and recordings; `tools/regenerate_trajectory_reference.py` regenerates `trajectory_reference.npz`.

EYESWEB_CORE_PATH: directory holding `eyesweb_core*.pyd` (the CMake build output of the private EyesWebCore repository: `EyesWebCore/build/Release`). It is put on `sys.path` before any
test module is collected, so tests need no path handling of their own. The core is optional: tests that need it skip.
"""

import os
import sys

if os.environ.get("EYESWEB_CORE_PATH"):
    sys.path.insert(0, os.environ["EYESWEB_CORE_PATH"])
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "_support"))

# The features are backed by the compiled core, so without it only the tests of the pure-Python data model can run.
try:
    import pyeyesweb._core  # noqa: F401
except ImportError:
    _PURE = ("test_output_contract.py",)

    def pytest_ignore_collect(collection_path, config):
        name = collection_path.name
        return name.startswith("test_") and name not in _PURE
