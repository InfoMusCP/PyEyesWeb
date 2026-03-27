# Notebook 4 — Feature Output Contracts: Result Dataclasses and `to_flat_dict()`

> **Learning Objectives**
> - Understand why PyEyesWeb returns typed dataclasses instead of raw floats
> - Inspect `FeatureResult` and its specialisations: `KineticEnergyResult`, `SmoothnessResult`, `ContractionExpansionResult`, `RarityResult`, `SuddennessResult`
> - Use `is_valid` to detect computation failures gracefully
> - Use `to_flat_dict(prefix=...)` to build a clean Pandas DataFrame logging pipeline
> - Export a multi-feature time-series table to CSV

---

## 0. Setup

```python
import numpy as np
import pandas as pd
from tqdm.auto import tqdm

from pyeyesweb.data_models import SlidingWindow
from pyeyesweb.low_level import KineticEnergy, BoundingBoxFilledArea, Smoothness, DirectionChange
from pyeyesweb.mid_level import Suddenness
from pyeyesweb.analysis_primitives import Rarity
from utils.data_loader import GestureDataLoader

loader = GestureDataLoader("data")
```

---

## 1. The Problem with Raw Floats

Imagine a feature that computes three things simultaneously: total kinetic energy, per-axis energy components, and per-joint energies. If the return type were a plain Python list, the caller would have to know (and remember) that:

- Index `0` is total energy
- Indices `1:4` are X/Y/Z components
- Indices `4:` are per-joint values

This is fragile, undocumented, and error-prone — especially when refactoring or routing data over a network (e.g., OSC).

**PyEyesWeb's solution**: every feature returns a strictly typed Python `@dataclass` that inherits from `FeatureResult`. Fields have names, types, and docstrings. Autocomplete works. Bugs are caught at definition time, not runtime.

---

## 2. The `FeatureResult` Base Class

```python
from pyeyesweb.data_models.results import FeatureResult
```

All result classes share two guarantees:

| Attribute / Method | Purpose |
|-------------------|---------|
| `is_valid: bool` | `True` if computation succeeded; `False` on failure (empty window, too few samples, degenerate geometry) |
| `to_flat_dict(prefix="")` | Flattens all fields to a dictionary of scalar values, optionally namespaced |

### 2.1 The `is_valid` contract — graceful failure

When a feature cannot produce a meaningful result, it returns a `FeatureResult` with `is_valid=False` rather than raising an exception. This is particularly important in real-time loops where a single bad frame should not crash the system.

```python
from pyeyesweb.data_models.results import FeatureResult

empty_window = SlidingWindow(max_length=60, n_signals=1, n_dims=1)
smooth_ft    = Smoothness(rate_hz=100.0)

result = smooth_ft(empty_window)   # Window is empty!
print(f"is_valid: {result.is_valid}")   # → False
print(f"sparc: {result.sparc}")          # → None (optional field, not computed)
```

In a real-time loop, you can use this cleanly:

```python
result = smooth_ft(window)
if result.is_valid:
    send_over_osc("/smoothness", result.sparc)
```

---

## 3. Anatomy of Specific Result Types

### 3.1 `KineticEnergyResult`

```python
pos_tensor, vel_tensor, _, marker_names = loader.load("trial10", sensor="qualisys")
N_frames, N_joints, N_dims = pos_tensor.shape

ef = KineticEnergy(weights=1.0, labels=marker_names)
sw = SlidingWindow(max_length=1, n_signals=N_joints, n_dims=3)
sw.append(vel_tensor[100, :, :])  # Append a single frame

result = ef(sw)
print(result)
```

**Output (condensed):**
```
KineticEnergyResult(
    is_valid=True,
    total_energy=0.423,
    component_energy=[0.102, 0.198, 0.123],   # X, Y, Z
    joints={
        "PELVIS":     {"total": 0.021, "components": [0.005, 0.010, 0.006]},
        "HAND_RIGHT": {"total": 0.054, "components": [0.019, 0.024, 0.011]},
        ...
    }
)
```

Accessing individual fields:

```python
print(f"Total energy     : {result.total_energy:.4f}")
print(f"Component X      : {result.component_energy[0]:.4f}")
print(f"HAND_RIGHT total : {result.joints['HAND_RIGHT']['total']:.4f}")
```

### 3.2 `SmoothnessResult`

```python
sf = Smoothness(rate_hz=100.0, metrics=["sparc", "jerk_rms"])
sw_speed = SlidingWindow(max_length=60, n_signals=1, n_dims=1)
hand_idx = marker_names.index("HAND_RIGHT")
hand_speed = np.linalg.norm(vel_tensor[:, hand_idx, :], axis=1)

for t in range(60):
    sw_speed.append(hand_speed[t])

result = sf(sw_speed)
print(result)
# → SmoothnessResult(is_valid=True, sparc=-2.341, jerk_rms=0.187)
print(f"SPARC    : {result.sparc:.3f}")
print(f"Jerk RMS : {result.jerk_rms:.3f}")
```

### 3.3 `ContractionExpansionResult`

```python
from pyeyesweb.low_level import BoundingBoxFilledArea, EllipsoidSphericity, PointsDensity

sw_pose = SlidingWindow(max_length=1, n_signals=N_joints, n_dims=3)
sw_pose.append(pos_tensor[100, :, :])

ci  = BoundingBoxFilledArea().compute(pos_tensor[100, :, :])
sph = EllipsoidSphericity().compute(pos_tensor[100, :, :])
pd_ = PointsDensity().compute(pos_tensor[100, :, :])

print(f"Contraction Index : {ci.contraction_index:.4f}")
print(f"Sphericity        : {sph.sphericity:.4f}")
print(f"Points Density    : {pd_.points_density:.4f} mm")
```

### 3.4 `SuddennessResult`

```python
from pyeyesweb.mid_level import Suddenness

hand_idx = marker_names.index("HAND_RIGHT")
sw_hand = SlidingWindow(max_length=120, n_signals=1, n_dims=3)
sdn_ft  = Suddenness()

for t in range(120):
    sw_hand.append(pos_tensor[t, hand_idx:hand_idx+1, :])

result = sdn_ft(sw_hand)
print(f"is_sudden : {result.is_sudden}")
print(f"alpha     : {result.alpha:.3f}  (stable distribution tail weight)")
print(f"beta      : {result.beta:.3f}   (skewness)")
print(f"gamma     : {result.gamma:.3f}  (scale)")
```

### 3.5 `RarityResult`

```python
from pyeyesweb.analysis_primitives import Rarity

# Push total kinetic energy values into a longer-horizon window
sw_energy_hist = SlidingWindow(max_length=300, n_signals=1, n_dims=1)
rarity_ft = Rarity(alpha=0.5)
ef2 = KineticEnergy(weights=1.0)
sw_vel = SlidingWindow(max_length=1, n_signals=N_joints, n_dims=3)

for t in range(300):
    sw_vel.append(vel_tensor[t, :, :])
    e_val = ef2(sw_vel).total_energy
    sw_energy_hist.append(e_val)

result = rarity_ft(sw_energy_hist)
print(f"Rarity score : {result.rarity:.4f}")
print("(0 = exactly average; higher = unusually high or low energy moment)")
```

---

## 4. `to_flat_dict()` — Flattening for Data Logging

Nested dataclasses are beautiful for code, but problematic for DataFrames and CSV files. `to_flat_dict()` recursively flattens the result into a `{str: scalar}` dictionary.

```python
# KineticEnergy has nested lists and dicts — to_flat_dict unpacks them
result = ef.compute(vel_tensor[100, :, :])
flat = result.to_flat_dict()
print(list(flat.keys())[:8])
# → ['is_valid', 'total_energy', 'energy_x', 'energy_y', 'energy_z',
#    'joint_PELVIS_total', 'joint_PELVIS_x', 'joint_PELVIS_y', ...]
```

### 4.1 The `prefix` argument — namespacing features

When logging multiple features into a single dictionary per frame, `prefix` prevents key collisions:

```python
e_flat  = ef.compute(vel_tensor[100, :, :]).to_flat_dict(prefix="energy")
ci_flat = BoundingBoxFilledArea().compute(pos_tensor[100, :, :]).to_flat_dict(prefix="contraction")

combined = {**e_flat, **ci_flat}
print(list(combined.keys())[:5])
# → ['energy_is_valid', 'energy_total_energy', 'energy_energy_x', ..., 'contraction_is_valid', ...]
```

---

## 5. Building a Full-Trial Feature Log → Pandas DataFrame

This is the canonical offline analysis pattern: iterate over all frames, extract features, accumulate flat dictionaries, and build a DataFrame in one shot.

```python
ef      = KineticEnergy(weights=1.0, labels=marker_names)
ci_ft   = BoundingBoxFilledArea()
sf      = Smoothness(rate_hz=100.0, metrics=["sparc", "jerk_rms"])

sw_vel  = SlidingWindow(max_length=1,  n_signals=N_joints, n_dims=3)
sw_pos  = SlidingWindow(max_length=1,  n_signals=N_joints, n_dims=3)
sw_spd  = SlidingWindow(max_length=60, n_signals=1,       n_dims=1)

hand_idx = marker_names.index("HAND_RIGHT")
hand_speed_arr = np.linalg.norm(vel_tensor[:, hand_idx, :], axis=1)

data_log = []

for t in tqdm(range(N_frames), desc="Building feature log"):
    sw_vel.append(vel_tensor[t, :, :])
    sw_pos.append(pos_tensor[t, :, :])
    sw_spd.append(hand_speed_arr[t])

    if not sw_spd.is_full:
        continue

    row = {"frame": t}
    row.update(ef(sw_vel).to_flat_dict(prefix="energy"))
    row.update(ci_ft(sw_pos).to_flat_dict(prefix="contraction"))
    row.update(sf(sw_spd).to_flat_dict(prefix="smooth"))
    data_log.append(row)

df = pd.DataFrame(data_log)
print(df.shape)
print(df[["frame", "energy_total_energy", "contraction_contraction_index", "smooth_sparc"]].head())
```

**Expected output (values will vary):**

```
(1472, 74)   ← 1472 frames after warm-up, 74 columns

   frame  energy_total_energy  contraction_contraction_index  smooth_sparc
0     60               0.4103                         0.6721        -2.341
1     61               0.3981                         0.6734        -2.388
2     62               0.4210                         0.6699        -2.302
...
```

---

## 6. Exporting the Feature Matrix to CSV

```python
output_path = "data/trial0001_features.csv"
df.to_csv(output_path, index=False)
print(f"Saved {len(df)} frames × {len(df.columns)} features to {output_path}")
```

This CSV can be directly imported into R, MATLAB, or any ML framework (scikit-learn, PyTorch, etc.) for statistical analysis or model training.

---

## 7. 🧪 Experiment: Filtering Invalid Rows

Not every frame produces valid results. For example, at trial boundaries or during sensor drop-outs, `is_valid=False` rows will appear. Practice filtering them:

```python
# Keep only rows where ALL features computed successfully
valid_mask = (
    (df["energy_is_valid"]      == True) &
    (df["contraction_is_valid"] == True) &
    (df["smooth_is_valid"]      == True)
)
df_clean = df[valid_mask].copy()
print(f"Valid frames: {len(df_clean)} / {len(df)}")
```

**Now try the following experiments:**
1. Add `Suddenness` to the log. Which joints / trials produce `is_sudden=True`?
2. Add `Rarity` on the energy signal (step: compute energy → push to a long-horizon window → compute rarity). What does a high rarity score correspond to visually?
3. Export three trials into separate CSVs and concatenate them with a `trial_id` column for between-trial comparison.

---

## Summary

| Result class | `is_valid` | Key fields | Nested content? |
|-------------|-----------|-----------|-----------------|
| `FeatureResult` | ✓ | — | No |
| `KineticEnergyResult` | ✓ | `total_energy`, `component_energy`, `joints` | Yes — `to_flat_dict` unpacks |
| `SmoothnessResult` | ✓ | `sparc`, `jerk_rms` | No |
| `ContractionExpansionResult` | ✓ | `contraction_index`, `sphericity`, `points_density` | No |
| `SuddennessResult` | ✓ | `is_sudden`, `alpha`, `beta`, `gamma` | No |
| `RarityResult` | ✓ | `rarity` | No |

In **Notebook 5**, we step back and explore the *scientific* rationale behind the feature hierarchy — the four-layer theoretical framework that gives each of these measurements its meaning.
