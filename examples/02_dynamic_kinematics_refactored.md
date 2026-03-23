# Dynamic Kinematics

> [!NOTE]
> **Educational Material**: Suitable for the PyEyesWeb Erasmus+ Project & MOCO Scientific Workshop
>
> **Learning Objectives**:
> * Extract dynamic metrics defined by velocity and acceleration.
> * Learn the difference between Time-Series history windows and Instantaneous windows.
> * Quantify movement Smoothness using SPARC and minimize mathematical edge-case errors.

While static posture evaluates geometry, **Kinematics** evaluates motion. In this notebook, we analyze the quality, direction, and energy of the subject's movement.

We will extract three features:
1. **Kinetic Energy**: The instantaneous physical energy of the movement.
2. **Smoothness (SPARC & Jerk)**: The mathematical fluidity of the trajectory.
3. **Direction Change**: How sharply the subject is altering their spatial trajectory.

## 1. Loading the Data
We load our standard position tensor, but this time we also explicitly need the Velocity and Acceleration tensors, as kinematics are physically defined by speed and acceleration over time. We utilize the `load_motion_data` tool to automatically parse the files.

```python
import numpy as np
from utils.data_loader import load_motion_data
from utils.plot_utils import plot_feature_timeseries

# Load data into clean 3D tensors
pos_tensor, vel_tensor, acc_tensor, marker_names = load_motion_data("data/trial0001_impulsive.tsv")
hand_idx = marker_names.index("HAND_RIGHT")

N_frames, N_joints, N_dims = pos_tensor.shape
print(f"Loaded {N_frames} frames tracking {N_joints} joints.")
```

## 2. Time-Series vs. Instantaneous Windows

Here we see the true power of the `SlidingWindow` architecture.

*   **Smoothness and Direction Change** are *Dynamic Features*. To know if a movement is smooth or changing direction, the algorithm must look at the historical trajectory over a period. We give them a long window (e.g., 60 frames latency).
*   **Kinetic Energy** evaluates the instantaneous state ($E_k = \frac{1}{2}mv^2$). Because we already calculated the velocity, the feature only needs to look at the *current frame*. We give it a window of exactly 1.

We will also use the `metrics` argument to explicitly choose which mathematical outputs we want from features that offer multiple formulations.

```python
from pyeyesweb.data_models import SlidingWindow
from pyeyesweb.low_level import Smoothness, DirectionChange, KineticEnergy

# 1. Initialize Windows
# Dynamic Windows (Require history)
sw_pos_traj = SlidingWindow(max_length=60, n_signals=N_joints, n_dims=3)

# Static Window (Requires only the current instant)
sw_vel = SlidingWindow(max_length=1, n_signals=N_joints, n_dims=3)

# 2. Initialize Features
smooth_feature = Smoothness(rate_hz=100.0, metrics=["sparc", "jerk_rms"])
direction_feature = DirectionChange(metrics=["polygon"]) # Uses polygon area enclosed by the trajectory
energy_feature = KineticEnergy(weights=1.0, labels=marker_names)
```

## 3. The Execution Loop
As we iterate through the frames, notice how we wait for the *longest* window (`sw_pos_traj`) to fully populate before we start saving our computations. This prevents mathematical artifacts (like exploding Jerk calculations due to missing historical data) from corrupting our outputs at the start of the trial.

```python
from tqdm.auto import tqdm

sparc_data = [] # Fluidity
dir_data = []   # Direction Change
energy_data = [] # Kinetic Energy

for t in tqdm(range(N_frames), desc="Processing Kinematics"):
    
    sw_pos_traj.update(pos_tensor[t, :, :])
    sw_vel.update(vel_tensor[t, :, :])
    
    if sw_pos_traj.is_full():
        
        # A. Kinetic Energy (Uses static window of Velocity)
        e_val = energy_feature.extract(sw_vel)
        energy_data.append(e_val)
        
        # B. Direction Change (Uses historical Position)
        hand_trajectory = sw_pos_traj.data[:, hand_idx:hand_idx+1, :]
        dir_val = direction_feature.extract(hand_trajectory)
        dir_data.append(dir_val["polygon"])
        
        # C. Smoothness (SPARC)
        # SPARC uses the Z-data trajectory to compute spectral arc lengths.
        # Pure 3D tensors are sliced to retrieve only the 1D Z-axis scalar over time.
        hand_pos_z = sw_pos_traj.data[:, hand_idx, 2:3]
        s_val = smooth_feature.extract(hand_pos_z)
        sparc_data.append(s_val["sparc"])

energy_data = np.array(energy_data)
dir_data = np.array(dir_data)
sparc_data = np.array(sparc_data)
```

## 4. Visualizing Dynamics
We can now correlate energy bursts with direction changes and fluidity breakdowns.

```python
time_axis = np.arange(len(energy_data)) / 100.0

plot_feature_timeseries(
    time_axis, 
    energy_data, 
    sparc_data, 
    dir_data,
    feature_names=["Kinetic Energy", "SPARC Smoothness", "Direction Change (Polygon)"],
    title="Kinematic Motion Dynamics"
)
```
