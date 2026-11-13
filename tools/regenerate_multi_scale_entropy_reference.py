"""Regenerate the expected records in `tests/data/multi_scale_entropy_reference.npz` (status, reason, timestamp and
outputs of every window of every case) with the current MultiScaleEntropy and EnsembleDominance, run as
`test_parity_multi_scale_entropy.py` runs them. The inputs (`case<i>`) and the parameters are kept. Do it ONLY when a
numeric change is intended. Needs the compiled core.
    python tools/regenerate_multi_scale_entropy_reference.py
"""

import json
import os
import sys
from pathlib import Path

import numpy as np

if os.environ.get("EYESWEB_CORE_PATH"):
    sys.path.insert(0, os.environ["EYESWEB_CORE_PATH"])
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pyeyesweb.analysis_primitives import MultiScaleEntropy  # noqa: E402
from pyeyesweb.data_models.results import Status  # noqa: E402
from pyeyesweb.high_level import EnsembleDominance  # noqa: E402

path = Path(__file__).resolve().parents[1] / "tests" / "data" / "multi_scale_entropy_reference.npz"
with np.load(path) as archive:
    data = {key: archive[key] for key in archive.files}
meta = json.loads(str(data["meta"]))


def floats(values):
    return [float(value) for value in np.asarray(values, dtype=float).reshape(-1)]


for index, entry in enumerate(meta):
    case = data[f"case{index}"]
    if entry["kind"] != "window" and not np.isfinite(case).all():
        continue  # a stream with a NaN sample is checked against the clean stream, not against records
    params = {("minimum_points" if name == "min_points" else name): value for name, value in entry["params"].items() if name != "methods"}
    feature, dominance = MultiScaleEntropy(**params), EnsembleDominance()
    if entry["kind"] == "window":
        results = [feature._process_window(case)]
    else:
        results = [feature.process(case[:, step], timestamp=entry["dt"] * (step + 1)) for step in range(case.shape[1])]
    records = []
    for result in results:
        outputs = {"complexity_index": floats(result.complexity_index) if result.status is Status.OK else [],
                   "dominance_score": [], "leader_index": 0.0, "leader_complexity": float("nan")}
        if result.status is Status.OK:
            composed = dominance.process(result.complexity_index)
            outputs.update(dominance_score=floats(composed.dominance_score), leader_index=float(composed.leader_index),
                           leader_complexity=float(composed.leader_complexity))
        records.append({"status": int(result.status), "reason": result.reason, "timestamp": float(result.timestamp),
                        "outputs": outputs})
    changed = records != entry["records"]
    entry["records"] = records
    print(f"{entry['name']}: {'changed' if changed else 'same'}")
data["meta"] = np.array(json.dumps(meta))
np.savez_compressed(path, **data)
