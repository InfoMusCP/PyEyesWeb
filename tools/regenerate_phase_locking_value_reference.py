"""Regenerate the expected records in `tests/data/phase_locking_value_reference.npz` (status, reason, timestamp and
`phase_locking_value` of every window of every case) with the current PhaseLockingValue, run as
`test_parity_plv.py` runs it. The inputs (`case<i>`) and the parameters are kept. Do it ONLY when a numeric change is
intended. Needs the compiled core.
    python tools/regenerate_phase_locking_value_reference.py
"""

import json
import os
import sys
from pathlib import Path

import numpy as np

if os.environ.get("EYESWEB_CORE_PATH"):
    sys.path.insert(0, os.environ["EYESWEB_CORE_PATH"])
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pyeyesweb.analysis_primitives.synchronization import PhaseLockingValue  # noqa: E402

path = Path(__file__).resolve().parents[1] / "tests" / "data" / "phase_locking_value_reference.npz"
with np.load(path) as archive:
    data = {key: archive[key] for key in archive.files}
meta = json.loads(str(data["meta"]))
for index, entry in enumerate(meta):
    case = data[f"case{index}"]
    if entry["kind"] != "window" and not np.isfinite(case).all():
        continue  # checked against the clean stream, not against records
    params = {name: tuple(value) if isinstance(value, list) else value for name, value in entry["params"].items()}
    feature = PhaseLockingValue(**params)
    if entry["kind"] == "window":
        results = [feature._process_window(case[:1], case[1:2])]
    else:
        results = [feature.process(case[0, step], case[1, step], timestamp=entry["dt"] * (step + 1))
                   for step in range(case.shape[1])]
    old = [record["outputs"]["phase_locking_value"] for record in entry["records"]]
    entry["records"] = [{"status": int(result.status), "reason": result.reason, "timestamp": float(result.timestamp),
                         "outputs": {"phase_locking_value": float(result["phase_locking_value"])}} for result in results]
    new = [record["outputs"]["phase_locking_value"] for record in entry["records"]]
    finite = [(a, b) for a, b in zip(old, new) if np.isfinite(a) or np.isfinite(b)]
    change = max((abs(a - b) for a, b in finite if np.isfinite(a) and np.isfinite(b)), default=0.0)
    print(f"{entry['name']}: largest change {change:.3f}; statuses {sorted({r['status'] for r in entry['records']})}")
data["meta"] = np.array(json.dumps(meta))
np.savez_compressed(path, **data)
