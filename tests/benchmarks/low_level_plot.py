import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

# --- Import your new library components ---
from pyeyesweb.data_models.sliding_window import SlidingWindow
from pyeyesweb.low_level.contraction_expansion import BoundingBoxFilledArea, EllipsoidSphericity, PointsDensity
from pyeyesweb.low_level.equilibrium import Equilibrium
from pyeyesweb.low_level.kinetic_energy import KineticEnergy
from pyeyesweb.low_level.direction_change import DirectionChange
from pyeyesweb.low_level.smoothness import Smoothness

# ==========================================
# 1. SETUP & CONFIGURATION
# ==========================================
fps = 30.0
sliding_window_len = 120
txt_file = "tests/benchmarks/trial00005.txt"

# ==========================================
# 2. DATA LOADING & PRE-PROCESSING
# ==========================================
print("Loading and cleaning data...")
df = pd.read_csv(txt_file, skiprows=4, sep="\t")
cols_to_keep = [c for c in df.columns if
                (c.endswith("x") or c.endswith("y") or c.endswith("z")) and "speed" not in c and "dist" not in c][2:]
df = df[cols_to_keep].drop_duplicates()

# Clean NaNs
df.replace(0, np.nan, inplace=True)
df.interpolate(method='linear', inplace=True)
df.bfill(inplace=True)
df.ffill(inplace=True)

# Extract axes (Matching your notebook's X, Z, Y ordering)
markersPosX = df.iloc[:, 0::3].values
markersPosZ = df.iloc[:, 1::3].values
markersPosY = df.iloc[:, 2::3].values
markers_names = [col[:-1] for col in df.iloc[:, 0::3].columns]

# Create Master Position Tensor: Shape (Time, N_joints, 3)
pos_tensor = np.stack([markersPosX, markersPosY, markersPosZ], axis=-1)
N_frames, N_joints, N_dims = pos_tensor.shape

# Calculate Master Velocity Tensor (Diff * FPS)
vel_tensor = np.zeros_like(pos_tensor)
vel_tensor[1:] = (pos_tensor[1:] - pos_tensor[:-1]) * fps

# Choose a joint for Smoothness (e.g., Rightwrist)
rightwrist_idx = markers_names.index("Rightwrist") if "Rightwrist" in markers_names else 0

# ==========================================
# 3. INITIALIZE PIPELINE & FEATURES
# ==========================================
# We use three distinct windows for the three types of data expected
sw_pos = SlidingWindow(max_length=sliding_window_len, n_signals=N_joints, n_dims=3)
sw_vel = SlidingWindow(max_length=sliding_window_len, n_signals=N_joints, n_dims=3)
sw_speed = SlidingWindow(max_length=sliding_window_len, n_signals=1, n_dims=1)

features = {
    "bb": BoundingBoxFilledArea(),
    "sphere": EllipsoidSphericity(),
    "density": PointsDensity(),
    # Mocking Equilibrium using wrists and neck (indices 4, 6, 5) if feet aren't present
    "eq": Equilibrium(left_foot_idx=4, right_foot_idx=6, barycenter_idx=5),
    "ke": KineticEnergy(weights=1.0, labels=markers_names),

    # UPDATED: Uses Strategy 2 API
    "dir1": DirectionChange(metrics=["polygon"]),
    "dir2": DirectionChange(metrics=["cosine"]),

    # Defaults to computing both SPARC and Jerk
    "smooth": Smoothness(rate_hz=fps)
}

all_results = []

# ==========================================
# 4. REAL-TIME SIMULATION LOOP
# ==========================================
print("Running features through sliding windows...")
for frame_idx in range(N_frames):
    # 1. Update Windows
    sw_pos.append(pos_tensor[frame_idx])
    sw_vel.append(vel_tensor[frame_idx])

    # Calculate 1D speed for the selected joint
    joint_speed = np.linalg.norm(vel_tensor[frame_idx, rightwrist_idx, :])
    sw_speed.append([[joint_speed]])  # Must match expected shape

    # 2. Compute Features & Flatten
    frame_results = {}

    # Features requiring positions
    frame_results.update(features["bb"](sw_pos).to_flat_dict("bb"))
    frame_results.update(features["sphere"](sw_pos).to_flat_dict("sphere"))
    frame_results.update(features["density"](sw_pos).to_flat_dict("density"))
    frame_results.update(features["eq"](sw_pos).to_flat_dict("eq"))
    frame_results.update(features["dir1"](sw_pos).to_flat_dict("dir1"))
    frame_results.update(features["dir2"](sw_pos).to_flat_dict("dir2"))
    # Feature requiring velocity
    frame_results.update(features["ke"](sw_vel).to_flat_dict("ke"))

    # Feature requiring 1D speed profile
    frame_results.update(features["smooth"](sw_speed).to_flat_dict("smooth"))

    all_results.append(frame_results)

# ==========================================
# 5. VISUALIZATION
# ==========================================
print("Plotting results...")
results_df = pd.DataFrame(all_results)
# print(results_df)
# exit(0)
# Filter out the is_valid flags just for cleaner plotting
metrics_to_plot = [
    "bb_contraction_index",
    "sphere_sphericity",
    "density_points_density",
    "ke_total_energy",
    "dir_polygon",  # UPDATED: Matches the new flat dict key
    "smooth_sparc",
    "smooth_jerk_rms"
]

fig, axes = plt.subplots(4, 2, figsize=(16, 10), sharex=True)
fig.suptitle("PyEyesWeb Low-Level Features Overview", fontsize=16)

axes = axes.flatten()
for idx, metric in enumerate(metrics_to_plot):
    if metric in results_df.columns:
        axes[idx].plot(results_df.index, results_df[metric], label=metric, color=f"C{idx}")
        axes[idx].set_title(metric)
        axes[idx].grid(True, linestyle="--", alpha=0.6)
        axes[idx].legend(loc="upper right")
    else:
        axes[idx].text(0.5, 0.5, f"{metric} not computed", ha='center')

plt.tight_layout()
plt.subplots_adjust(top=0.92)
plt.savefig("feature_validation_plot.png", dpi=150)
plt.show()