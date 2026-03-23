# Bilateral Symmetry Analysis

> [!NOTE]
> **Educational Material**: Suitable for the PyEyesWeb Erasmus+ Project & MOCO Scientific Workshop
>
> **Learning Objectives**:
> * Combine spatial orientation with complex analysis logic.
> * Evaluate clinical and physical limb mirroring (Geometric Symmetry).
> * Handle unrolled feature dictionaries.

Welcome to the final tutorial! In the previous notebook, we used `Synchronization` to determine if the left and right hands were moving at the same *time* (Temporal Phase). 

In this notebook, we look at **Geometric Symmetry**: Are the left and right limbs physically mirroring each other in 3D space?

This is a critical metric in clinical rehabilitation (e.g., assessing gait symmetry during walking after a stroke) and sports biomechanics. We will evaluate the spatial mirroring of the hands and feet relative to the body's center.

## 1. Loading the Data & Identifying Joints
We use the `load_motion_data` tool to parse the tensor. To calculate bilateral symmetry, we need to explicitly tell the algorithm which joints represent the "Left" side, which represent the "Right" side, and which joint represents the "Center of Symmetry" (usually the Spine or Pelvis).

```python
from utils.data_loader import load_motion_data
from utils.plot_utils import plot_feature_timeseries

# Load spatial data
pos_tensor, _, _, marker_names = load_motion_data("data/trial0001_impulsive.tsv")

# Identify the indices for our left/right pairs and our center
l_hand_idx = marker_names.index("HAND_LEFT")
r_hand_idx = marker_names.index("HAND_RIGHT")

l_foot_idx = marker_names.index("FOOT_LEFT")
r_foot_idx = marker_names.index("FOOT_RIGHT")

# We will use the Spine Base (Pelvis) as our 0,0,0 reflection point
center_idx = marker_names.index("SPINE_BASE")

print(f"Tracking Symmetry for Hands ({l_hand_idx}, {r_hand_idx}) and Feet ({l_foot_idx}, {r_foot_idx})")
print(f"Center of Symmetry: PELVIS ({center_idx})")
```

```text
Output:
Tracking Symmetry for Hands (11, 12) and Feet (19, 20)
Center of Symmetry: PELVIS (0)
```

## 2. Setting up the Symmetry Feature
How does the algorithm actually calculate symmetry?

For every frame, it shifts the 3D coordinate system so the `center_idx` is exactly at the origin `(0,0,0)`. It then takes the Right joint, mathematically reflects it across the sagittal plane (the X-axis), and measures the straight Euclidean distance to the Left joint.

$$Error = || Left - Reflected(Right) ||$$

Because frame-by-frame spatial tracking can be micro-jittery, `GeometricSymmetry` is implemented as a **Dynamic Feature**. It averages this spatial error over a rolling sliding window to output a smooth, robust evaluation of the subject's overall posture.

```python
from pyeyesweb.data_models import SlidingWindow
from pyeyesweb.low_level import GeometricSymmetry

# 1. Initialize Window
# We use a 30-frame (~0.3 seconds) window to smooth out micro-jitters
sw_pos = SlidingWindow(max_length=30, n_signals=pos_tensor.shape[1], n_dims=3)

# 2. Initialize Feature
# We pass a list of tuples defining our explicit pairs
joint_pairs = [
    (l_hand_idx, r_hand_idx),
    (l_foot_idx, r_foot_idx)
]

symmetry_feature = GeometricSymmetry(
    joint_pairs=joint_pairs,
    center_of_symmetry=center_idx
)

print(f"Initialized Window Shape: {sw_pos.data.shape}")
```

```text
Output:
Initialized Window Shape: (30, 21, 3)
```

## 3. The Execution Loop
Because `GeometricSymmetry` evaluates multiple pairs at once, it outputs a hierarchical Result object. We can use the helper method `.to_flat_dict("sym")` to automatically unroll our pairs list into easy-to-read dictionary keys, perfectly formatted for a Pandas DataFrame or a logging system.

```python
import numpy as np
from tqdm.auto import tqdm

hand_sym_data = []
foot_sym_data = []

for t in tqdm(range(pos_tensor.shape[0]), desc="Evaluating Symmetry"):
    
    sw_pos.update(pos_tensor[t, :, :])
    
    if sw_pos.is_full():
        # Extract and unroll the results
        res = symmetry_feature.extract(sw_pos)
        flat_results = res.to_flat_dict("sym")
        
        # The flat dictionary keys are structured dynamically: prefix_pair_{left}_{right}
        hand_key = f"sym_pair_{l_hand_idx}_{r_hand_idx}"
        foot_key = f"sym_pair_{l_foot_idx}_{r_foot_idx}"
        
        hand_sym_data.append(flat_results[hand_key])
        foot_sym_data.append(flat_results[foot_key])
        
        # Verify first output
        if len(hand_sym_data) == 1:
            print(f"Frame {t} -> Hand Sym Error: {flat_results[hand_key]:.2f}, Foot Sym Error: {flat_results[foot_key]:.2f}")

hand_sym_data = np.array(hand_sym_data)
foot_sym_data = np.array(foot_sym_data)
```

## 4. Visualizing Asymmetry Error
*Note: This feature measures Asymmetry Error. Therefore, a value of 0.0 indicates perfect mirror-symmetry, while higher values indicate asymmetric breaking.*

```python
time_axis = np.arange(len(hand_sym_data)) / 100.0

plot_feature_timeseries(
    time_axis, 
    hand_sym_data, 
    foot_sym_data, 
    feature_names=["Hand Symmetry Error", "Foot Symmetry Error"],
    title="Clinical Geometric Symmetry"
)
```
