# Notebook 3 — The Dual API: Real-Time Streaming vs. Offline Analysis

> **Learning Objectives**
> - Understand the Streaming API (`__call__` with `SlidingWindow`) and its role in live systems
> - Understand the Pure Math API (`.compute()` with a raw NumPy array) and its offline efficiency
> - Prove that both APIs produce equivalent results on the same data
> - Know when to choose each API for your use case

---

## 0. Setup

```python
import numpy as np
import matplotlib.pyplot as plt
from tqdm.auto import tqdm

from pyeyesweb.data_models import SlidingWindow
from pyeyesweb.low_level import KineticEnergy, BoundingBoxFilledArea, Smoothness
from utils.data_loader import load_qualisys_tsv
```

---

## 1. Two Contexts, One Library

PyEyesWeb was designed to serve two radically different usage contexts:

### Context A — Live Performance / Real-Time System

A researcher or artist connects a motion capture system (Qualisys, OptiTrack, Kinect, IMU) to a data routing environment (MaxMSP, TouchDesigner, ROS). Data arrives over OSC or a serial port **one frame at a time**, at up to 240 Hz. There is no "recording" yet — each frame is new and must be processed immediately.

```
OSC stream → Python listener → SlidingWindow.append(frame) → feature(window)
                                                                 ↓
                                                          result → OSC out → visualiser
```

### Context B — Offline Scientific Analysis

A researcher has already collected 25 trial recordings (.tsv, .txt, .csv files). They want to batch-process all files overnight and produce a feature matrix for statistical analysis or machine learning.

```
Load file → pos_tensor (T, N, D) → feature.compute(pos_tensor) → DataFrame → CSV
```

The **same Python classes and feature objects** serve both contexts. The two paths are:

| | Streaming API | Pure Math API |
|--|--------------|---------------|
| **Method** | `feature(window)` — `__call__` | `feature.compute(array)` |
| **Input** | A `SlidingWindow` instance | A raw NumPy array |
| **State** | Stateful (reads from buffer) | Stateless (operates on the array directly) |
| **Best for** | Frame-by-frame live processing | Bulk offline processing |
| **Output** | Same `FeatureResult` dataclass | Same `FeatureResult` dataclass |

---

## 2. The Streaming API — Simulating Live Processing

In this section we simulate a live streaming pipeline using a pre-recorded file. The loop mimics exactly what happens when frames arrive over a network: we iterate one frame at a time, append to the window, and extract the feature.

### 2.1 Load data

```python
pos_tensor, vel_tensor, acc_tensor, marker_names = load_qualisys_tsv(
    "data/trial0001_impulsive.tsv"
)
N_frames, N_joints, N_dims = pos_tensor.shape
hand_idx = marker_names.index("HAND_RIGHT")

print(f"Loaded {N_frames} frames × {N_joints} joints × {N_dims} dims")
```

### 2.2 Set up the Streaming pipeline

```python
# Window for KineticEnergy (Static, needs velocity of current frame)
sw_vel = SlidingWindow(max_length=1, n_signals=N_joints, n_dims=3)

# Window for Smoothness (Dynamic, needs a speed history of 60 frames)
sw_speed = SlidingWindow(max_length=60, n_signals=1, n_dims=1)

energy_ft = KineticEnergy(weights=1.0, labels=marker_names)
smooth_ft  = Smoothness(rate_hz=100.0, metrics=["sparc"])

streaming_energy = []
streaming_sparc  = []
streaming_frames = []

for t in tqdm(range(N_frames), desc="Streaming API"):
    # --- Frame arrives ---
    hand_speed = np.linalg.norm(vel_tensor[t, hand_idx, :])

    sw_vel.append(vel_tensor[t, :, :])    # shape (21, 3)
    sw_speed.append(hand_speed)            # shape (1,)

    # --- Streaming feature extraction ---
    e_result = energy_ft(sw_vel)
    streaming_energy.append(e_result.total_energy)

    if sw_speed.is_full:
        s_result = smooth_ft(sw_speed)
        streaming_sparc.append(s_result.sparc)
        streaming_frames.append(t)

streaming_energy = np.array(streaming_energy)
streaming_sparc  = np.array(streaming_sparc)
print(f"\nStreaming complete. Energy samples: {len(streaming_energy)}, SPARC samples: {len(streaming_sparc)}")
```

---

## 3. The Pure Math API — Bulk Offline Processing

When you have the full recording loaded as a tensor, you can skip the simulation loop entirely. The `.compute()` method accepts the **whole 3-D tensor** for dynamic features, or a **single 2-D frame** for static features.

> **Important**: For `DynamicFeature.compute()`, input shape is `(Time, N_signals, N_dims)`.  
> For `StaticFeature.compute()`, input shape is `(N_signals, N_dims)` — a single frame.

### 3.1 Offline KineticEnergy — process each frame independently

`KineticEnergy` is a `StaticFeature`: its `.compute()` takes one frame `(N_joints, 3)`. To get a full time-series, we use a vectorised list comprehension or a simple loop.

```python
offline_energy = np.array([
    energy_ft.compute(vel_tensor[t, :, :]).total_energy
    for t in range(N_frames)
])
print(f"Offline energy shape: {offline_energy.shape}")
```

### 3.2 Offline Smoothness — process in rolling windows

`Smoothness` is a `DynamicFeature`: its `.compute()` takes a 3-D tensor `(Time, 1, 1)` (or the squeezed 1-D array). We replicate the same rolling-window logic without a `SlidingWindow` object:

```python
WINDOW = 60
hand_speed_full = np.linalg.norm(vel_tensor[:, hand_idx, :], axis=1)  # (T,)

offline_sparc  = []
offline_frames = []

for t in range(WINDOW, N_frames):
    window_slice = hand_speed_full[t - WINDOW : t]   # (60,) 1-D speed profile
    # compute() requires shape (T, n_signals, n_dims) for DynamicFeature
    # Smoothness internally calls .ravel(), so we can pass the 1-D slice directly
    result = smooth_ft.compute(window_slice.reshape(-1, 1, 1))
    offline_sparc.append(result.sparc)
    offline_frames.append(t)

offline_sparc = np.array(offline_sparc)
print(f"Offline SPARC shape: {offline_sparc.shape}")
```

---

## 4. Equivalence Check — Both APIs Must Agree

The streaming and offline results should be numerically identical (within floating-point precision). Let us verify:

```python
# Align the two SPARC series (streaming starts at frame 60, offline at frame 60)
n_compare = min(len(streaming_sparc), len(offline_sparc))
max_diff   = np.max(np.abs(streaming_sparc[:n_compare] - offline_sparc[:n_compare]))
print(f"Max SPARC difference between APIs: {max_diff:.2e}")
# → Max SPARC difference between APIs: ~0.00e+00 (or very close to machine precision)
```

```python
# Visual comparison
fig, axes = plt.subplots(2, 1, figsize=(14, 6))

axes[0].plot(streaming_energy, label="Streaming API", alpha=0.8)
axes[0].plot(offline_energy,   label="Offline API",   alpha=0.5, linestyle="--")
axes[0].set_title("KineticEnergy — API Comparison")
axes[0].legend()

axes[1].plot(streaming_frames[:n_compare], streaming_sparc[:n_compare],
             label="Streaming API", alpha=0.8)
axes[1].plot(offline_frames[:n_compare],  offline_sparc[:n_compare],
             label="Offline API", alpha=0.5, linestyle="--")
axes[1].set_title("Smoothness (SPARC) — API Comparison")
axes[1].legend()

plt.tight_layout()
plt.show()
```

> The two curves should be perfectly overlapping. This confirms that the `SlidingWindow` is simply a *convenience wrapper* around the same underlying `compute()` mathematics.

---

## 5. When to Use Each API

### Use the Streaming API when:
- Processing live data in a real-time loop (OSC, WebSocket, serial port)
- Building interactive installations where results must appear within milliseconds of movement
- The `SlidingWindow` state needs to persist across many frames (it handles the circular buffer for you)

### Use the Pure Math API when:
- Analysing a collection of pre-recorded trial files
- Running parameter sweeps (e.g., testing 10 different `rate_hz` values overnight)
- Building feature matrices for machine learning
- Writing unit tests for feature correctness

### Performance note

The Pure Math API on a full recording is typically **significantly faster** than the simulated streaming loop, because the Python `for` loop overhead is eliminated and NumPy can use vectorised operations across the entire time axis.

```python
import time

# Time the streaming approach
t0 = time.perf_counter()
sw = SlidingWindow(max_length=1, n_signals=N_joints, n_dims=3)
ef = KineticEnergy()
for t in range(N_frames):
    sw.append(vel_tensor[t])
    ef(sw)
streaming_time = time.perf_counter() - t0

# Time the offline approach
t0 = time.perf_counter()
ef2 = KineticEnergy()
for t in range(N_frames):
    ef2.compute(vel_tensor[t])
offline_time = time.perf_counter() - t0

print(f"Streaming: {streaming_time:.3f} s")
print(f"Offline:   {offline_time:.3f} s")
```

---

## 6. Compositing Both APIs in a Research Pipeline

A real research workflow often combines both paths: the Pure Math API for bulk feature extraction, and the Streaming API for live inspection or debugging.

```python
# --- Offline bulk pass: extract energy for all 3 trials ---
TRIALS = [
    "data/trial0001_impulsive.tsv",
    "data/trial0002_impulsive.tsv",
    "data/trial0003_impulsive.tsv",
]

ef = KineticEnergy()
summary = {}

for path in TRIALS:
    pos, vel, acc, names = load_qualisys_tsv(path)
    energies = np.array([
        ef.compute(vel[t, :, :]).total_energy for t in range(vel.shape[0])
    ])
    summary[path] = {
        "mean_energy": energies.mean(),
        "max_energy":  energies.max(),
        "n_frames":    len(energies),
    }
    print(f"{path}: mean={energies.mean():.2f}, peak={energies.max():.2f}")
```

---

## 7. 🧪 Experiment: Cross-Sensor API Comparison

Once you have data from multiple sensors, use the Pure Math API to process all trials rapidly and compare features across modalities. This experiment template will work with any loader that returns `(pos, vel, acc, names)` tuples:

```python
# Placeholder — replace with your actual loaders when data is available
# from utils.data_loader import load_imu_data, load_kinect_data, load_qualisys_tsv

# --- For each sensor type ---
# sensor_data = {
#     "Qualisys": load_qualisys_tsv("data/qualisys_trial01.tsv"),
#     "Kinect":   load_kinect_data("data/kinect_trial01.???"),
#     "IMU":      load_imu_data("data/imu_trial01.???"),
# }

# ef = KineticEnergy()
# for sensor, (pos, vel, acc, names) in sensor_data.items():
#     energies = np.array([ef.compute(vel[t]).total_energy for t in range(vel.shape[0])])
#     print(f"{sensor:10s}: mean={energies.mean():.3f}, peak={energies.max():.3f}")
```

**Questions to reflect on:**
1. Is the KineticEnergy output comparable across Qualisys and Kinect if both track the same 21 joints in metric coordinates?
2. How does the IMU energy profile differ if the sensor is placed on the wrist vs. the torso?
3. Does the Pure Math API execute noticeably faster on the Qualisys files (higher-dimensional data) vs. the IMU files (lower-dimensional)?

---

## Summary

| | Streaming API | Pure Math API |
|--|--------------|---------------|
| **Method** | `feature(window)` | `feature.compute(array)` |
| **State** | Stateful (circular buffer) | Stateless |
| **Loop required** | Yes — frame by frame | Optional (can vectorise) |
| **Use case** | Real-time systems | Offline batch analysis |
| **Speed** | Loop overhead per frame | Vectorised, faster for batches |
| **Output** | Identical | Identical |

In **Notebook 4**, we will open up the `FeatureResult` objects returned by both APIs and learn how to introspect, log, and serialize their structured contents.
