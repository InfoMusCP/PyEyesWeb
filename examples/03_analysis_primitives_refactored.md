# Analysis Primitives

> [!NOTE]
> **Educational Material**: Suitable for the PyEyesWeb Erasmus+ Project & MOCO Scientific Workshop
>
> **Learning Objectives**:
> * Understand Analysis Primitives as abstract mathematical tools independent of biomechanics.
> * Use Primitives to evaluate Rarity (Probability) and Volatility (Statistics).
> * Measure Bimanual Coordination using the Temporal Phase Locking Value (Synchronization).

Welcome to the Analysis Primitives tutorial! While our previous notebooks focused on the spatial geometry and physical kinematics of the body, this notebook focuses purely on **Statistics and Signal Processing**. 

Analysis Primitives are domain-agnostic mathematical tools. You can feed them 3D trajectories, 1D speeds, or even the output of *other* features!

In this tutorial, we will evaluate the speeds of the subject's hands to answer three questions:
1. **Rarity**: Is the current speed of the hand an anomalous outlier compared to its past behavior?
2. **Statistical Moments**: What is the rolling historical average and volatility (standard deviation) of the movement?
3. **Synchronization**: Are the left and right hands phase-locked (oscillating together in time)?

## 1. Loading the Data
We use the universal `load_motion_data` function to parse the file automatically. We will extract the indices for both hands, as we want to check their inter-limb synchronization.

```python
import numpy as np
from utils.data_loader import load_motion_data
from utils.plot_utils import plot_feature_timeseries

# Load the data
pos_tensor, vel_tensor, _, marker_names = load_motion_data("data/trial0001_impulsive.tsv")

right_hand_idx = marker_names.index("HAND_RIGHT")
left_hand_idx = marker_names.index("HAND_LEFT")

N_frames = pos_tensor.shape[0]
print(f"Loaded {N_frames} frames. Ready to analyze bimanual coordination!")
```

## 2. Setting up the Primitives
We will set up specific `SlidingWindow` instances for our primitives:
*   **Rarity & Statistics**: These evaluate a single 1-Dimensional signal (the right hand's speed), so they need a 1D window (`n_signals=1, n_dims=1`).
*   **Synchronization**: This evaluates the Temporal Phase Locking Value (PLV) between *two* signals to see if they are correlated. It requires a window with two signals (`n_signals=2`).

> **Mathematical Note**: Rarity uses a rolling probability distribution. It calculates the histogram of the sliding window and evaluates the probability of the *current* frame happening, compared to the probability of the *most common* bin. High rarity indicates a sudden, highly unexpected behavior.

```python
from pyeyesweb.data_models import SlidingWindow
from pyeyesweb.analysis_primitives import Rarity, StatisticalMoment, Synchronization

# 1. Initialize Windows
sw_single_speed = SlidingWindow(max_length=100, n_signals=1, n_dims=1)
sw_dual_speed = SlidingWindow(max_length=100, n_signals=2, n_dims=1)

# 2. Initialize Features
rarity_feature = Rarity(alpha=0.5)

# We can explicitly filter which moments we want (Mean, Variance, Skew, Kurtosis)
stats_feature = StatisticalMoment(metrics=["mean", "std_dev"])

# Phase Locking Value (PLV)
sync_feature = Synchronization(filter_params=None) 
```

## 3. The Execution Loop
As we loop through the velocity tensor, we will calculate the 1D magnitude of the speed for both hands. Notice how we format the data when pushing it into the dual-signal window.

```python
from tqdm.auto import tqdm

rarity_data = []
sync_data = []
volatility_data = []

for t in tqdm(range(N_frames), desc="Processing Primitives"):
    
    # Calculate Real 1D Speed (Euclidean Norm of 3D Velocity)
    r_speed = np.linalg.norm(vel_tensor[t, right_hand_idx, :])
    l_speed = np.linalg.norm(vel_tensor[t, left_hand_idx, :])
    
    # Push into windows
    # Shape must correctly wrap indices: (1, 1, 1) for single, (1, 2, 1) for dual
    sw_single_speed.update(np.array([[[r_speed]]]))
    sw_dual_speed.update(np.array([[[r_speed], [l_speed]]]))
    
    if sw_dual_speed.is_full():
        
        # A. Rarity
        r_val = rarity_feature.extract(sw_single_speed)
        rarity_data.append(r_val)
        
        # B. Volatility (Standard Deviation)
        stat_val = stats_feature.extract(sw_single_speed)
        volatility_data.append(stat_val["std_dev"])
        
        # C. Phase Locking Synchronization
        s_val = sync_feature.extract(sw_dual_speed)
        sync_data.append(s_val["plv"])

rarity_data = np.array(rarity_data)
volatility_data = np.array(volatility_data)
sync_data = np.array(sync_data)
```

## 4. Visualizing Probability and Phase
Let's plot the statistical footprint of the motion! Here we can see when the movement becomes highly unexpected, how volatile the window behaves, and when the two hands enter a phase-locked temporal rhythm.

```python
time_axis = np.arange(len(sync_data)) / 100.0

plot_feature_timeseries(
    time_axis, 
    rarity_data, 
    volatility_data, 
    sync_data,
    feature_names=["Rarity (Probability Outlier)", "Volatility (Std Deviation)", "Bimanual Synchronization (PLV)"],
    title="Statistical Analysis Primitives"
)
```
