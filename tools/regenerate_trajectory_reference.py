"""Regenerate `tests/data/trajectory_reference.npz`, the frozen outputs `test_trajectory_parity.py` compares against, from
the current features. Do it ONLY when a numeric change is intended. Needs the compiled core (EYESWEB_CORE_PATH).
    python tools/regenerate_trajectory_reference.py
"""

import json
import os
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tests" / "unit_tests"))
if os.environ.get("EYESWEB_CORE_PATH"):
    sys.path.insert(0, os.environ["EYESWEB_CORE_PATH"])

import test_trajectory_parity as parity  # noqa: E402

values, meta = parity._pack(parity.compute())
np.savez_compressed(parity.REFERENCE, meta=json.dumps(meta), values=values)
print(f"{len(meta)} cases, {len(values)} values, {parity.REFERENCE.stat().st_size} bytes")
