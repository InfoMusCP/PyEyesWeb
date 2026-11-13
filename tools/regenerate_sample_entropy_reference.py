"""Regenerate the outputs in `tests/data/sample_entropy_reference.npz` (`entropy<i>` of every case) with the current core.
The signals (`signal<i>`) and the cases (`meta`) are kept. Do it ONLY when a numeric change is intended. Needs the compiled
core.
    python tools/regenerate_sample_entropy_reference.py
"""

import json
import os
import sys
from pathlib import Path

import numpy as np

if os.environ.get("EYESWEB_CORE_PATH"):
    sys.path.insert(0, os.environ["EYESWEB_CORE_PATH"])
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pyeyesweb.analysis_primitives import SampleEntropy  # noqa: E402

path = Path(__file__).resolve().parents[1] / "tests" / "data" / "sample_entropy_reference.npz"
with np.load(path) as archive:
    data = {key: archive[key] for key in archive.files}
meta = json.loads(str(data["meta"]))
for index, entry in enumerate(meta):
    signal = data[f"signal{index}"]
    feature = SampleEntropy(window=len(signal), embedding_dimension=entry["embedding_dimension"], tolerance=entry["tolerance"])
    new = np.asarray(feature._process_window(signal)["sample_entropy"], dtype=data[f"entropy{index}"].dtype)
    changed = not np.array_equal(new, data[f"entropy{index}"], equal_nan=True)
    print(f"{entry['name']}: {'changed' if changed else 'same'}")
    data[f"entropy{index}"] = new
np.savez_compressed(path, **data)
