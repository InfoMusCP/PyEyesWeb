"""Regenerate the outputs in `tests/data/gesture_segmenter_reference.npz` (status, reason, values, valid of every scenario) with
the current KineticEnergy + MotionNoiseDetector + GestureSegmenter, `is_noisy` fed directly to the `noise` input. The inputs
(`syn_*`, `ts_*`) and the scenarios (`meta`) are kept. Do it ONLY when a numeric change is intended. Needs the compiled core.
    python tools/regenerate_gesture_segmenter_reference.py
"""

import os
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tests" / "unit_tests"))
if os.environ.get("EYESWEB_CORE_PATH"):
    sys.path.insert(0, os.environ["EYESWEB_CORE_PATH"])

import test_parity_gesture_segmenter as parity  # noqa: E402

path = parity.DATA / "gesture_segmenter_reference.npz"
data = {key: parity.REFERENCE[key] for key in parity.REFERENCE.files}
for scenario in parity.SCENARIOS:
    rows = parity.compute(scenario)
    name = scenario["name"]
    data[name + "_status"] = np.array([row[0] for row in rows], dtype=data[name + "_status"].dtype)
    data[name + "_reason"] = np.array([row[1] for row in rows], dtype=data[name + "_reason"].dtype)
    data[name + "_values"] = np.array([row[2] for row in rows])
    data[name + "_valid"] = np.array([row[3] for row in rows])
np.savez_compressed(path, **data)
print(f"{len(parity.SCENARIOS)} scenarios, {path.stat().st_size} bytes")
