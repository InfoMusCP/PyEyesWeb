# Notebook 5 — The Theoretical Framework: Layers of Movement Description

> **Learning Objectives**
> - Understand the four-layer conceptual model underpinning PyEyesWeb
> - Learn the role of **timescale** in distinguishing Layer 2 from Layer 3
> - Map Python subpackages (`low_level`, `mid_level`, `analysis_primitives`) to framework layers
> - Learn to stack primitives on top of low-level outputs to create higher-level descriptors
> - Experiment with features from each layer across different gesture types

---

## 0. Setup

```python
import numpy as np
import matplotlib.pyplot as plt
from tqdm.auto import tqdm

from pyeyesweb.data_models import SlidingWindow
from pyeyesweb.low_level import (
    KineticEnergy, BoundingBoxFilledArea, EllipsoidSphericity,
    PointsDensity, Smoothness, DirectionChange, Equilibrium, GeometricSymmetry
)
from pyeyesweb.mid_level import Impulsivity, Lightness, Suddenness
from pyeyesweb.analysis_primitives import (
    Rarity, StatisticalMoment, Synchronization
)
from utils.data_loader import load_qualisys_tsv
```

---

## 1. The Big Picture: From Coordinates to Expression

Motion capture systems give us raw numbers: a stream of `(X, Y, Z)` positions for each tracked joint, at each millisecond. That is all.

Yet when we observe a human body in motion, we perceive vastly more: intention, effort, rhythm, grace, tension, surprise. The gap between `[0.32, 1.14, 0.08]` and "she moves with sudden lightness" is enormous.

PyEyesWeb bridges this gap through a **four-layer conceptual model** developed in the DANCE project and implemented in the EyesWeb computational framework.

```
Layer 4 — Expressive Qualities      (perception, context, memory, emotion)
     ↑
Layer 3 — Mid-Level Features        (amodal qualities: lightness, suddenness, fluidity)
     ↑
Layer 2 — Low-Level Features        (biomechanics: energy, velocity, geometry)
     ↑
Layer 1 — Physical Signals          (raw sensor data: X, Y, Z coordinates)

                ↕  (applied at all layers)
Analysis Primitives                   (universal tools: statistics, entropy, synchronization)
```

> **Critical insight**: This is a **conceptual model**, not a strict computation pipeline. The arrows indicate semantic grounding, not mandatory computation order. You can compute Layer 3 features directly from Layer 1 data. The model tells you *what* a feature means, not *how* you must call it.

---

## 2. Layer 1 — Physical Signals: The Raw Input

Layer 1 is everything that comes out of a sensor before PyEyesWeb touches it.

| Sensor type | Signal | Shape per frame |
|-------------|--------|-----------------|
| Qualisys optical | 3D joint positions | `(N_joints, 3)` |
| Kinect RGB-D | 3D skeleton joints | `(N_joints, 3)` |
| Body-worn IMU | Linear acceleration + angular velocity | `(1, 6)` or two `(1, 3)` arrays |

```python
pos_tensor, vel_tensor, acc_tensor, marker_names = load_qualisys_tsv(
    "data/trial0001_impulsive.tsv"
)
N_frames, N_joints, N_dims = pos_tensor.shape
print(f"Layer 1 data: {N_frames} frames, {N_joints} joints, {N_dims} dims")
print(f"Markers: {marker_names}")
```

Typical preprocessing applied at Layer 1 (before PyEyesWeb features):
- **Denoising / smoothing** (Savitzky-Golay filter — available via `pyeyesweb.utils.signal_processing`)
- **Gap filling** (linear interpolation for missing Qualisys markers)
- **Velocity extraction** (`np.gradient` or finite differences)

```python
# Finite difference velocity (mm/s if positions are in mm)
vel_approx = np.gradient(pos_tensor, axis=0) * 100.0  # × sampling rate
```

---

## 3. Layer 2 — Low-Level Features: Biological Truth

Layer 2 features describe the **objective physical state** of the body. They answer questions with no ambiguity: What is the kinetic energy? How large is the bounding volume? Are the joints symmetrically distributed?

Layer 2 features are predominantly **Static** (single frame) or use **short windows (~0.5 s)**.

### 3.1 Spatial Geometry (instantaneous body shape)

```python
hand_idx = marker_names.index("HAND_RIGHT")

ci_ft  = BoundingBoxFilledArea()  # How compact is the pose?
sph_ft = EllipsoidSphericity()    # How spherical vs. elongated is the body volume?
pd_ft  = PointsDensity()          # How dispersed are joints around the barycenter?
sym_ft = GeometricSymmetry()      # How symmetric are left and right sides?

frame = pos_tensor[100, :, :]     # (21, 3)

print(f"Contraction index : {ci_ft.compute(frame).contraction_index:.3f}")
print(f"Sphericity        : {sph_ft.compute(frame).sphericity:.3f}")
print(f"Points density    : {pd_ft.compute(frame).points_density:.1f} mm")
```

### 3.2 Raw Kinematics (instantaneous physics)

```python
sw_vel = SlidingWindow(max_length=1, n_signals=N_joints, n_dims=3)
sw_vel.append(vel_tensor[100, :, :])

ef  = KineticEnergy(weights=1.0, labels=marker_names)
result = ef(sw_vel)
print(f"Total kinetic energy    : {result.total_energy:.4f}")
print(f"Right hand contribution : {result.joints['HAND_RIGHT']['total']:.4f}")
```

### 3.3 Trajectory properties (short-window, ~0.5 s)

```python
sf   = Smoothness(rate_hz=100.0, metrics=["sparc"])
dc_ft = DirectionChange()

hand_speed = np.linalg.norm(vel_tensor[:, hand_idx, :], axis=1)

sw_speed = SlidingWindow(max_length=60, n_signals=1, n_dims=1)
sw_hand_pos = SlidingWindow(max_length=60, n_signals=1, n_dims=3)

for t in range(60):
    sw_speed.append(hand_speed[t])
    sw_hand_pos.append(pos_tensor[t, hand_idx:hand_idx+1, :])

print(f"Smoothness (SPARC)   : {sf(sw_speed).sparc:.3f}")
print(f"Direction change     : {dc_ft(sw_hand_pos).polygon:.4f}")
```

---

## 4. Layer 3 — Mid-Level Features: Expressive Quality

Mid-Level features step away from strict physics and enter the domain of **perception and quality**. They are inspired by **Laban Movement Analysis (LMA)** and the qualitative vocabulary used by dancers, physiotherapists, and movement scientists.

Key distinguishing properties:
- They operate over **longer windows (0.5–3 s)** or **movement units** (a complete reach, a gait cycle)
- They are **amodal** — the same concept (e.g., "suddenness") can be computed from Qualisys data, Kinect data, or IMU data
- They describe *how* a movement is performed, not *what* its physical parameters are

Layer 3 features in `pyeyesweb.mid_level`:

| Feature | Concept | Key output |
|---------|---------|-----------|
| `Suddenness` | Is the velocity distribution heavy-tailed? (stable distribution fit) | `is_sudden`, `alpha` |
| `Impulsivity` | Does the movement exhibit short, sharp velocity bursts? | TBD per implementation |
| `Lightness` | Is the movement characterised by low weight-bearing and floating quality? | TBD per implementation |

```python
from pyeyesweb.mid_level import Suddenness

sdn_ft = Suddenness()
sw_sudden = SlidingWindow(max_length=120, n_signals=1, n_dims=3)

for t in range(120):
    sw_sudden.append(pos_tensor[t, hand_idx:hand_idx+1, :])

result = sdn_ft(sw_sudden)
print(f"Sudden movement: {result.is_sudden}")
print(f"Alpha (tail weight): {result.alpha:.3f}  — closer to 2=Gaussian, closer to 1=heavy tail/sudden")
```

### 4.1 The Timescale Distinction

The most important conceptual difference between Layer 2 and Layer 3 is **timescale**:

```
Layer 2:  short windows (~0.5 s) → "What is the velocity right now?"
Layer 3:  longer windows (1–3 s) → "Was this movement suddenly impulsive over the last few seconds?"
```

The same feature class can operate at different layers depending on its window:

```python
# SPARC at Layer 2 (60 frames = 0.6 s) — fine-grained smoothness
#   "Is this specific gesture smooth?"
sf_l2 = Smoothness(rate_hz=100.0)
sw_l2 = SlidingWindow(max_length=60,  n_signals=1, n_dims=1)

# SPARC at Layer 3 (300 frames = 3 s) — sustained quality
#   "Is this phrase of movement overall smooth?"
sf_l3 = Smoothness(rate_hz=100.0)
sw_l3 = SlidingWindow(max_length=300, n_signals=1, n_dims=1)

# Fill both and compare
for t in range(300):
    sw_l2.append(hand_speed[t])
    sw_l3.append(hand_speed[t])

r_l2 = sf_l2(sw_l2) if sw_l2.is_full else None
r_l3 = sf_l3(sw_l3) if sw_l3.is_full else None
print(f"L2 SPARC (0.6s window): {r_l2.sparc:.3f}")
print(f"L3 SPARC (3.0s window): {r_l3.sparc:.3f}")
```

> **Notice**: The L3 value is less sensitive to momentary speed fluctuations. It captures a broader, more phrase-level description of quality.

---

## 5. Analysis Primitives — Universal Building Blocks

The `analysis_primitives` subpackage contains **domain-agnostic tools** that know nothing about human movement. They operate on any data array. What makes them powerful is that you can **apply them to the outputs of other features**, composing a richer analysis.

| Primitive | What it measures | Typical use |
|-----------|-----------------|-------------|
| `Rarity` | How atypical is the latest value vs. the historical distribution? | Flag unusual energy spikes or rare postures |
| `StatisticalMoment` | Mean, variance, skewness, kurtosis of a window | Describe the distribution of any signal |
| `Synchronization` | Are two signals moving together? (cross-correlation) | Hand-foot coupling, bilateral coordination |
| `Clusterability` | Does the window data cluster into distinct groups? | Identify repetitive vs. exploratory movement |
| `MseDominance` | Multi-scale entropy — regularity vs. complexity | Characterise movement predictability |

### 5.1 Stacking example: Energy → Rarity

This pipeline asks: *"Is the current kinetic energy unusually high or low relative to the last 3 seconds?"*

```python
from pyeyesweb.analysis_primitives import Rarity

ef       = KineticEnergy(weights=1.0)
rarity_ft = Rarity(alpha=0.5)

sw_vel       = SlidingWindow(max_length=1,   n_signals=N_joints, n_dims=3)
sw_energy_hist = SlidingWindow(max_length=300, n_signals=1,    n_dims=1)

log_energy = []
log_rarity = []

for t in tqdm(range(N_frames), desc="Energy → Rarity pipeline"):
    sw_vel.append(vel_tensor[t, :, :])
    e_val = ef(sw_vel).total_energy
    sw_energy_hist.append(e_val)

    log_energy.append(e_val)

    if sw_energy_hist.is_full:
        log_rarity.append(rarity_ft(sw_energy_hist).rarity)

# Plot
fig, axes = plt.subplots(2, 1, figsize=(14, 6))
axes[0].plot(log_energy, color="steelblue")
axes[0].set_title("Layer 2: Kinetic Energy (instantaneous)")
axes[0].set_ylabel("Energy")

rarity_start = N_frames - len(log_rarity)
axes[1].plot(range(rarity_start, N_frames), log_rarity, color="darkorange")
axes[1].set_title("Primitive: Rarity of Energy (relative to 3-second history)")
axes[1].set_ylabel("Rarity Score")

plt.tight_layout()
plt.show()
```

> **Reading the plot**: A rarity spike indicates a moment where kinetic energy fell into an unusual part of the distribution seen over the previous 3 seconds. This is more meaningful than a raw energy spike — it captures *surprise* relative to the movement's own history.

### 5.2 Stacking example: Signal Synchronization

*"Are the right hand and left hand moving in phase?"*

```python
from pyeyesweb.analysis_primitives import Synchronization

left_idx  = marker_names.index("HAND_LEFT")
right_idx = marker_names.index("HAND_RIGHT")

speed_left  = np.linalg.norm(vel_tensor[:, left_idx, :],  axis=1)
speed_right = np.linalg.norm(vel_tensor[:, right_idx, :], axis=1)

sync_ft = Synchronization()
sw_lr = SlidingWindow(max_length=120, n_signals=2, n_dims=1)

log_sync = []
for t in range(N_frames):
    sample = np.array([[speed_left[t]], [speed_right[t]]])  # (2, 1)
    sw_lr.append(sample)
    if sw_lr.is_full:
        result = sync_ft(sw_lr)
        log_sync.append(result)
```

---

## 6. 🧪 Experiment: Layer-by-Layer Feature Tour on Different Gestures

For each gesture trial available in your dataset, compute one feature from each layer and observe which features are most informative:

```python
TRIALS = [
    ("data/trial0001_impulsive.tsv", "Impulsive 1"),
    ("data/trial0002_impulsive.tsv", "Impulsive 2"),
    ("data/trial0003_impulsive.tsv", "Impulsive 3"),
    # Add more trials when available
]

ef  = KineticEnergy(weights=1.0)
sf  = Smoothness(rate_hz=100.0, metrics=["sparc"])
sdn = Suddenness()
rar = Rarity(alpha=0.5)

print(f"{'Trial':<25} | {'Mean Energy':>11} | {'Mean SPARC':>10} | {'% Sudden':>9} | {'Mean Rarity':>11}")
print("-" * 75)

for path, label in TRIALS:
    pos, vel, acc, names = load_qualisys_tsv(path)
    h_idx  = names.index("HAND_RIGHT") if "HAND_RIGHT" in names else 0
    h_spd  = np.linalg.norm(vel[:, h_idx, :], axis=1)
    T      = pos.shape[0]

    sw_v = SlidingWindow(max_length=1,   n_signals=pos.shape[1], n_dims=3)
    sw_s = SlidingWindow(max_length=60,  n_signals=1, n_dims=1)
    sw_d = SlidingWindow(max_length=120, n_signals=1, n_dims=3)
    sw_r = SlidingWindow(max_length=300, n_signals=1, n_dims=1)

    energies, sparcs, suddens, rarities = [], [], [], []

    for t in range(T):
        sw_v.append(vel[t])
        sw_s.append(h_spd[t])
        sw_d.append(pos[t, h_idx:h_idx+1, :])
        e_val = ef(sw_v).total_energy
        sw_r.append(e_val)
        energies.append(e_val)

        if sw_s.is_full:
            sparcs.append(sf(sw_s).sparc)
        if sw_d.is_full:
            suddens.append(sdn(sw_d).is_sudden)
        if sw_r.is_full:
            rarities.append(rar(sw_r).rarity)

    pct_sudden = 100 * np.mean(suddens) if suddens else 0
    print(f"{label:<25} | {np.mean(energies):>11.3f} | {np.mean(sparcs) if sparcs else 0:>10.3f} | {pct_sudden:>8.1f}% | {np.mean(rarities) if rarities else 0:>11.4f}")
```

**Reflection questions:**
1. Which trials have the most sudden movements (high `% Sudden`)? Does this match your visual inspection of the gesture?
2. Does the SPARC value track your intuition about smoothness? Are impulsive gestures always less smooth?
3. How does the Energy Rarity score relate to the absolute energy? Can a low-energy gesture have high rarity?

---

## Summary

| Layer | Subpackage | Timescale | Key question |
|-------|-----------|-----------|-------------|
| 1 — Physical Signals | (external input) | Instantaneous | What did the sensor measure? |
| 2 — Low-Level | `pyeyesweb.low_level` | ~0.1–0.5 s | What is the body's objective physical state? |
| 3 — Mid-Level | `pyeyesweb.mid_level` | ~0.5–3 s | What expressive quality does the movement have? |
| 4 — Expressive | (not yet implemented) | Phrases, context | What does an observer perceive and feel? |
| Primitives | `pyeyesweb.analysis_primitives` | Configurable | Can be applied at any layer to any signal |

In **Notebook 6**, we bring everything together in a capstone that explores how the choice of sensor and gesture type interacts with the features from each layer.
