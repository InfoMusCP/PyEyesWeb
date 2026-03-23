# Static Posture Analysis

> [!NOTE]
> **Educational Material**: Suitable for the PyEyesWeb Erasmus+ Project & MOCO Scientific Workshop
>
> **Learning Objectives**:
> * Differentiate static posture geometry from dynamic motion.
> * Extract the **Contraction Index** (Bounding Box vs Convex Hull).
> * Extract the **Points Density** (Dispersion from Barycenter).

Welcome to the first deep-dive tutorial! In expressive movement and biomechanical analysis, we often need to evaluate the spatial geometry of the body at a specific point in time, completely independent of how fast the subject is moving.

In this notebook, we will explore **Contraction** and **Expansion**. We will calculate two distinct geometric metrics:
1. **Contraction Index**: Compares the surface area of the body's Convex Hull (the tightest geometric wrapper) to its Axis-Aligned Bounding Box (AABB).
2. **Points Density**: Calculates the average dispersion (distance) of all joints from the body's barycenter (center of mass).

## 1. Loading the Data
As always, we begin by loading our motion capture data into our standard 3D tensor format: `(Time, Joints, Dimensions)`. Since static features only care about spatial coordinates, we will solely rely on the `pos_tensor`. We use the opaque `load_motion_data` to automatically ingest the file.

```python
from utils.data_loader import load_motion_data
from utils.plot_utils import plot_feature_timeseries

# Load the data
pos_tensor, vel_tensor, acc_tensor, marker_names = load_motion_data("data/trial0001_impulsive.tsv") 

N_frames, N_joints, N_dims = pos_tensor.shape
print(f"Loaded {N_frames} frames tracking {N_joints} joints.")
```

## 2. Setting up Static Features

Because these features are purely static, they do not need historical data to compute a result. Therefore, we can set the `SlidingWindow` maximum length to exactly 1.

> **Note on the Math**: The Contraction Index evaluates how much space the body takes up relative to its absolute dimensional limits. 
> 
> $$Contraction Index = \frac{SurfaceArea_{Hull}^2}{SurfaceArea_{BBox}}$$
> 
> When a dancer throws their arms and legs wide, their Convex Hull stretches to fill their Bounding Box, resulting in a high Contraction Index (Expansion). When they curl into a tight ball, the index drops.

```python
from pyeyesweb.data_models import SlidingWindow
from pyeyesweb.low_level import BoundingBoxFilledArea, PointsDensity

# 1. Initialize Window
# A static feature only needs the most recent frame!
sw_pos = SlidingWindow(max_length=1, n_signals=N_joints, n_dims=3)

# 2. Initialize Features
contraction_feature = BoundingBoxFilledArea()
density_feature = PointsDensity()
```

## 3. The Execution Loop
We iterate through the spatial data frame-by-frame.

```python
import numpy as np
from tqdm.auto import tqdm

contraction_data = []
density_data = []

# Iterate over Time
for t in tqdm(range(N_frames), desc="Processing Geometry"):
    
    # 1. Push newest frame into the sliding window
    sw_pos.update(pos_tensor[t, :, :])
    
    if sw_pos.is_full():
        # 2. Extract Features
        c_val = contraction_feature.extract(sw_pos)
        d_val = density_feature.extract(sw_pos)
        
        contraction_data.append(c_val)
        density_data.append(d_val)

# Convert to Numpy Arrays
contraction_data = np.array(contraction_data)
density_data = np.array(density_data)
```

## 4. Visualizing Geometry Expansion
We plot the results side-by-side to understand the correlation between Bounding Box contraction and Mass dispersion.

```python
time_axis = np.arange(len(contraction_data)) / 100.0 # Assuming 100 FPS

plot_feature_timeseries(
    time_axis, 
    contraction_data, 
    density_data, 
    feature_names=["Contraction Index (Area)", "Points Density"],
    title="Static Postural Expansion & Contraction"
)
```
