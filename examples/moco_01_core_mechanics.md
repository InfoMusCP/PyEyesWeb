# Notebook 1: The Core Mechanics (Time, State, and API)

> [!NOTE]
> **Educational Material**: PyEyesWeb Erasmus+ Project & MOCO Scientific Workshop
>
> **Learning Objectives**:
> *   Understand the dual-API architecture: Real-time (`__call__`) vs. Offline (`.compute()`).
> *   Master the `SlidingWindow` data structure for state management.
> *   Differentiate between Static (instantaneous) and Dynamic (trajectory-based) features.
> *   Explore structured output dataclasses.

Welcome to PyEyesWeb! This library is designed to extract expressive and biomechanical features from motion data. 

Before we discuss *what* we measure (the philosophy of movement), we must first understand *how* the system processes data. Movement occurs over time. Analyzing it requires us to intelligently manage time, state, and memory.

## 1. The Dual API: Real-time vs. Offline

PyEyesWeb is unique because it was built from the ground up for **live, real-time performance systems** (e.g., OSC streams from Optitrack/Kinect in MaxMSP or TouchDesigner), while still supporting traditional, offline data science workflows.

To support both worlds, every feature in the library exposes two distinct methods of execution:

### A. The Streaming API (`__call__`)
Designed for **live data**. As frames arrive one by one from your capture system, you feed them into the feature. The feature is *stateful*—it remembers what happened a second ago using a buffer.

```python
from pyeyesweb.low_level import KineticEnergy

# Initialize the feature
energy_feature_live = KineticEnergy()

# --- Inside a live OSC message loop (e.g., at 120 FPS) ---
# frame_data arrives from the network...
# energy_output = energy_feature_live(window_buffer) 
```

### B. The Pure Math API (`.compute()`)
Designed for **offline analysis**. When you already have a recorded CSV/TSV file, you don't need to simulate time passing frame-by-frame. You pass a purely stateless NumPy array to `.compute()`, and it rapidly calculates the entire matrix at once using vectorized C-level math.

```python
import numpy as np
from pyeyesweb.low_level import KineticEnergy

# Initialize the feature
energy_feature_offline = KineticEnergy()

# --- For offline CSV/Dataframe analysis ---
# full_recording is a massive numpy array of shape (Time, Joints, Dimensions)
# full_energy_timeseries = energy_feature_offline.compute(full_recording)
```

In this workshop, we will focus primarily on the **Streaming API**, as it prepares you for building interactive, real-time systems.

---

## 2. Managing Time with `SlidingWindow`

If the Streaming API takes data frame-by-frame, how does it know what happened a second ago? We solve this with the `SlidingWindow`. 

A `SlidingWindow` is a circular buffer. You tell it its `max_length` (e.g., 60 frames = 0.5 seconds at 120 FPS). Once it fills up, adding a new frame seamlessly pushes the oldest frame out.

```python
from pyeyesweb.data_models import SlidingWindow
import numpy as np

# Let's say we are tracking 21 joints in 3D space
N_joints = 21
N_dims = 3

# We want a 60-frame memory latency
window_60_frames = SlidingWindow(max_length=60, n_signals=N_joints, n_dims=3)

# Simulating incoming frames...
for t in range(100):
    dummy_frame = np.random.rand(N_joints, N_dims)
    window_60_frames.append(dummy_frame)
    
print(f"Window is full: {window_60_frames.is_full}")
print(f"Stored Data Shape: {window_60_frames.data.shape} (Time, Joints, Dims)")
```

> **Why check `is_full`?** If an algorithm requires 1 second of history to calculate smoothness, it will crash or return garbage data if you ask it for an answer on frame 2. We always wait for the window to fill before starting feature extraction.

---

## 3. Static vs. Dynamic Features

Every feature in PyEyesWeb is strictly classified purely by how much memory it needs to run.

### Static Features (Memory = 1 Frame)
These features calculate the **instantaneous state** of the body. 
*   *Example*: How much spatial area is the body taking up right now? What is the velocity at this exact millisecond? 
*   *Implementation*: They operate on a `SlidingWindow` with `max_length=1`.

### Dynamic Features (Memory > 1 Frame)
These features evaluate a **trajectory over time**.
*   *Example*: Did the dancer change direction sharply? Was the movement smooth over the last second? 
*   *Implementation*: They require a `SlidingWindow` with a `max_length` tailored to the requested latency (e.g., 60 to 120 frames).

Let's load real data and see this in action:

```python
from utils.data_loader import load_motion_data
from pyeyesweb.low_level import BoundingBoxFilledArea, DirectionChange

# 1. Load data
pos_tensor, _, _, marker_names = load_motion_data("data/trial0001_impulsive.tsv")
hand_idx = marker_names.index("HAND_RIGHT")

# 2. Setup Windows
# Static feature (Contraction) only needs 1 frame
window_static = SlidingWindow(max_length=1, n_signals=21, n_dims=3) 

# Dynamic feature (Direction Change) needs history (e.g., 60 frames) to see the trajectory curve
window_dynamic = SlidingWindow(max_length=60, n_signals=1, n_dims=3) # Tracking just the Hand

# 3. Setup Features
contraction_feature = BoundingBoxFilledArea()
direction_feature = DirectionChange(metrics=["polygon"])

# We wait for the dynamic window to fill, then we can extract!
for t in range(70): 
    window_static.append(pos_tensor[t, :, :])
    window_dynamic.append(pos_tensor[t, hand_idx:hand_idx+1, :]) # Send the 1x3 vector

print("Ready to process!")
```

---

## 4. Structured Output: Dataclasses over Floats

When you extract a feature in PyEyesWeb, it almost never returns a raw float (e.g., `0.85`). Why? Because many biomechanical algorithms produce multiple relevant metrics, and returning a generic list `[0.85, 1.2, 0.5]` is incredibly error-prone.

Instead, every feature returns a strictly typed `Dataclass`.

```python
# Evaluate both features using their respective fully-populated windows!
static_result = contraction_feature(window_static)
dynamic_result = direction_feature(window_dynamic)

print("--- Contraction (Static) Output ---")
print(static_result)
print(f"Extracted Index: {static_result.contraction_index:.3f}\n")

print("--- Direction Change (Dynamic) Output ---")
print(dynamic_result)
print(f"Extracted Polygon Area: {dynamic_result.polygon:.3f}")
```

Notice how `direction_feature` might also compute path curvature or circularity, all bundled safely inside its dataclass struct. This guarantees that whether you are plotting in Jupyter or routing over OSC to a synthesizer, your data architecture remains robust.

Now that we understand the flow of time and state, it's time to dive into the philosophical foundation of *what* we are actually extracting in Notebook 2!
