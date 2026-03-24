# Quickstart: The PyEyesWeb Pipeline

> [!NOTE]
> **Educational Material**: Suitable for the PyEyesWeb Erasmus+ Project & MOCO Scientific Workshop
>
> **Learning Objectives**:
> * Familiarize with the `load_motion_data` opaque data loader.
> * Understand the core `SlidingWindow` pipeline.
> * Extract three sample features (Static, Dynamic, and Primitive).

Welcome to PyEyesWeb! This library is designed to extract expressive and biomechanical features from motion data in real-time. 

## Understanding the Architecture: Concepts vs. Implementation

PyEyesWeb separates **what** we measure (the conceptual framework) from **how** it is computed (the implementation API).

### 1. The Conceptual Framework (What we measure)
*   **Low-Level Features**: Physical biomechanics, including spatial geometry (Contraction, Expansion) and raw kinematics (Kinetic Energy, Velocity).
*   **Mid-Level Features**: Qualitative, expressive aspects of movement that represent behavior or intent (e.g., Smoothness, Directness, Rhythmicity).
*   **Analysis Primitives**: Domain-agnostic mathematical and statistical tools (e.g., Probability/Rarity, Signal Synchronization, Volatility) that can be applied to any data stream.

### 2. The Implementation API (How we compute it)
Every feature in PyEyesWeb provides a dual-API structure depending on your use case:
*   **The Streaming API (`__call__`)**: Designed for real-time applications. You pass a `SlidingWindow` directly to the feature instance (e.g., `feature(window)`), and it automatically handles the buffer and state logic.
*   **The Pure Math API (`.compute()`)**: Designed for offline, bulk data processing. You pass a raw NumPy array (e.g., `feature.compute(array)`), making it stateless and highly optimized for data science.

Furthermore, every metric is implemented as either a **Static** or **Dynamic** feature, defined purely by its memory requirements:
*   **Static Features**: Require only the instantaneous state of the *current frame*. For example, the spatial Contraction of a single pose, or instantaneous Kinetic Energy. They operate on a sliding window of size 1.
*   **Dynamic Features**: Require a historical trajectory to evaluate changes *over time*. For example, checking if a movement was Smooth over the last second. They require a rolling sliding window to store past frames.

In this quickstart, we will build a unified pipeline extracting three metrics that cross-reference these categories (Concept vs Implementation details):
1. **Contraction** (Concept: Low-Level Geometry | API: Static Feature)
2. **Kinetic Energy** (Concept: Low-Level Kinematics | API: Static Feature)
3. **Smoothness** (Concept: Mid-Level Expressivity | API: Dynamic Feature | *Note: implemented structurally within `low_level`*)

## 1. Universal Data Loading
PyEyesWeb uses an opaque data loader that intuitively adapts to different file formats (like `.tsv` and `.txt`) to abstract away complex format parsing. It automatically infers header rows, missing values, axis groupings, and extracts the 3D Tensor kinematics.

```python
from utils.data_loader import load_qualisys_tsv
from utils.plot_utils import plot_feature_timeseries

# Load data into clean 3D tensors: (Time, Joints, Dimensions)
pos_tensor, vel_tensor, acc_tensor, marker_names = load_qualisys_tsv("data/trial0001_impulsive.tsv")

# Let's track the Right Hand
hand_idx = marker_names.index("HAND_RIGHT")

N_frames, N_joints, N_dims = pos_tensor.shape
print(f"Loaded {N_frames} frames tracking {N_joints} joints.")
print(f"Position Tensor Shape: ({N_frames}, {N_joints}, {N_dims})")
```

```text
Output:
Loaded 1532 frames tracking 21 joints.
Position Tensor Shape: (1532, 21, 3)
```

## 2. Real-Time Setup using Sliding Windows
Real-time streaming analysis requires processing data as it arrives sequentially frame-by-frame. PyEyesWeb manages this continuous flow of data using a `SlidingWindow` object to store a brief history of recent frames.

```python
from pyeyesweb.data_models import SlidingWindow

# Initialize a Window that holds the past 60 frames of position data
sw_pos = SlidingWindow(max_length=60, n_signals=N_joints, n_dims=3)

# Initialize a Window for velocity 
# (Kinematic Energy only needs the instantaneous velocity of the current frame! max_length=1)
sw_vel = SlidingWindow(max_length=1, n_signals=N_joints, n_dims=3)

# Initialize a Window for hand speed
# (Smoothness computes based on a 1D speed profile, so we need a dedicated 1D window)
sw_hand_speed = SlidingWindow(max_length=60, n_signals=1, n_dims=1)

print(f"Initialized Position Window Shape: {sw_pos.max_length} frames")
print(f"Initialized Velocity Window Shape: {sw_vel.max_length} frames")
```

```text
Output:
Initialized Position Window Shape: 60 frames
Initialized Velocity Window Shape: 1 frames
```

## 3. Initializing the Features
PyEyesWeb provides direct API exports for all mathematical features.

```python
from pyeyesweb.low_level import BoundingBoxFilledArea, KineticEnergy, Smoothness

contraction_feature = BoundingBoxFilledArea()
energy_feature = KineticEnergy(weights=1.0, labels=marker_names)
smooth_feature = Smoothness(rate_hz=100.0, metrics=["sparc", "jerk_rms"])
```

## 4. The Processing Loop
Now, we iterate through the pre-recorded data exactly as if it was arriving live via OSC from Qualisys or OptiTrack. We step frame-by-frame, push the newest coordinate to the `SlidingWindow`, and ask the Features to evaluate the current window state.

```python
import numpy as np
from tqdm.auto import tqdm

# We will store our computed feature values here as a list of dictionaries
data_log = []

# Iterate over Time
for t in tqdm(range(N_frames), desc="Processing Pipeline"):
    
    # 1. Update the Sliding Windows with the new incoming frame
    sw_pos.append(pos_tensor[t, :, :])
    sw_vel.append(vel_tensor[t, :, :])
    
    # Smoothness expects a 1D Speed Profile. We compute the right hand's 
    # scalar speed from its 3D velocity and push it to the speed window
    hand_velocity = vel_tensor[t, hand_idx, :]
    hand_speed = np.linalg.norm(hand_velocity)
    sw_hand_speed.append(hand_speed)
    
    # Only calculate dynamic features if the window is fully populated
    # (To avoid mathematical errors during the first few frames)
    if sw_pos.is_full:
        # --- Feature Extraction Using the Streaming API (__call__) ---
        
        # 1. Contraction (Static Feature evaluating Low-Level Geometry)
        c_result = contraction_feature(sw_pos)
        
        # 2. Kinetic Energy (Static Feature evaluating Low-Level Kinematics)
        e_result = energy_feature(sw_vel)
        
        # 3. Smoothness (Dynamic Feature evaluating Mid-Level Expressivity)
        s_result = smooth_feature(sw_hand_speed)
        
        # Group metrics for this frame
        frame_metrics = {
            "Contraction": c_result.contraction_index,
            "Energy": e_result.total_energy,
            "Smoothness (SPARC)": s_result.sparc
        }
        data_log.append(frame_metrics)
        
        # Print the very first result to verify transformations
        if len(data_log) == 1:
            print(f"Frame {t} -> Contraction: {frame_metrics['Contraction']:.2f}, Energy: {frame_metrics['Energy']:.2f}, Smoothness: {frame_metrics['Smoothness (SPARC)']:.2f}") 

```

## 5. Visualizing the Expressive Data
Let's see how these biomechanical/expressive qualities evolve over time!

```python
# The plotting utility expects a list of dictionaries, which perfectly 
# matches our data_log format. It handles dataframe conversion internally.
plot_feature_timeseries(
    results_list=data_log,
    metrics_to_plot=["Contraction", "Energy", "Smoothness (SPARC)"],
    title="Unified Metric Pipeline"
)
```
