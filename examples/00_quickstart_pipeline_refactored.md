# Quickstart: The PyEyesWeb Pipeline

> [!NOTE]
> **Educational Material**: Suitable for the PyEyesWeb Erasmus+ Project & MOCO Scientific Workshop
>
> **Learning Objectives**:
> * Familiarize with the `load_motion_data` opaque data loader.
> * Understand the core `SlidingWindow` pipeline.
> * Extract three sample features (Static, Dynamic, and Primitive).

Welcome to PyEyesWeb! This library is designed to extract expressive and biomechanical features from motion data in real-time. 

In this quickstart, we will build a complete, unified pipeline that extracts:
1. **A Static Feature**: Bounding Box Contraction (How folded/expanded is the body?)
2. **A Dynamic Feature**: Kinetic Energy (How much total energy is in the movement?)
3. **An Analysis Primitive**: Smoothness (How fluid is the right hand moving?)

## 1. Universal Data Loading
PyEyesWeb uses an opaque data loader that intuitively adapts to different file formats (like `.tsv` and `.txt`) to abstract away complex format parsing. It automatically infers header rows, missing values, axis groupings, and extracts the 3D Tensor kinematics.

```python
from utils.data_loader import load_motion_data
from utils.plot_utils import plot_feature_timeseries

# Load data into clean 3D tensors: (Time, Joints, Dimensions)
pos_tensor, vel_tensor, acc_tensor, marker_names = load_motion_data("data/trial0001_impulsive.tsv")

# Let's track the Right Hand
hand_idx = marker_names.index("HAND_RIGHT")

N_frames, N_joints, N_dims = pos_tensor.shape
print(f"Loaded {N_frames} frames tracking {N_joints} joints.")
```

## 2. Real-Time Setup using Sliding Windows
Real-time pipelines cannot peek into the future; they only know the past and the present. PyEyesWeb simulates this using a `SlidingWindow` object.

```python
from pyeyesweb.data_models import SlidingWindow

# Initialize a Window that holds the past 60 frames of position data
sw_pos = SlidingWindow(max_length=60, n_signals=N_joints, n_dims=3)

# Initialize a Window for velocity 
# (Energy only needs the current instant, so max_length=1 is sufficient!)
sw_vel = SlidingWindow(max_length=1, n_signals=N_joints, n_dims=3)
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

# We will store our computed feature values here
contraction_data = []
energy_data = []
smoothness_data = []

# Iterate over Time
for t in tqdm(range(N_frames), desc="Processing Pipeline"):
    
    # 1. Update the Sliding Windows with the new incoming frame
    sw_pos.update(pos_tensor[t, :, :])
    sw_vel.update(vel_tensor[t, :, :])
    
    # Only calculate dynamic features if the window is fully populated
    # (To avoid mathematical errors during the first few frames)
    if sw_pos.is_full():
        # --- Feature Extraction ---
        
        # A. Static Feature (uses recent position window)
        c_val = contraction_feature.extract(sw_pos)
        contraction_data.append(c_val)
        
        # B. Dynamic Feature (uses velocity window)
        e_val = energy_feature.extract(sw_vel)
        energy_data.append(e_val)
        
        # C. Analysis Primitive (specifically, SPARC smoothness of the right hand)
        # Slicing the tensor: we only pass the Z-axis of the right hand to SPARC
        hand_pos_z = sw_pos.data[:, hand_idx, 2:3] # Shape: (60, 1, 1)
        s_val = smooth_feature.extract(hand_pos_z)
        smoothness_data.append(s_val["sparc"]) 

# Convert to Numpy Arrays for plotting
contraction_data = np.array(contraction_data)
energy_data = np.array(energy_data)
smoothness_data = np.array(smoothness_data)
```

## 5. Visualizing the Expressive Data
Let's see how these biomechanical/expressive qualities evolve over time!

```python
time_axis = np.arange(len(contraction_data)) / 100.0 # Assuming 100 FPS

plot_feature_timeseries(
    time_axis, 
    energy_data,
    smoothness_data,
    contraction_data,
    feature_names=["Kinetic Energy", "SPARC Smoothness", "Contraction Index"],
    title="Unified Metric Pipeline"
)
```
