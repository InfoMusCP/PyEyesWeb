import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

# --- Import library components ---
from pyeyesweb.data_models.sliding_window import SlidingWindow
from pyeyesweb.analysis_primitives.clusterability import Clusterability
from pyeyesweb.analysis_primitives.rarity import Rarity
from pyeyesweb.analysis_primitives.statistical_moment import StatisticalMoment
from pyeyesweb.analysis_primitives.synchronization import Synchronization
from pyeyesweb.low_level.geometric_symmetry import GeometricSymmetry

# ==========================================
# 1. SETUP & DATA LOADING
# ==========================================
fps = 30.0
sliding_window_len = 100
txt_file = "tests/benchmarks/trial00005.txt"

print("Loading and cleaning data...")
df = pd.read_csv(txt_file, skiprows=4, sep="\t")
cols_to_keep = [c for c in df.columns if
                (c.endswith("x") or c.endswith("y") or c.endswith("z")) and "speed" not in c and "dist" not in c][2:]
df = df[cols_to_keep].drop_duplicates()
df.replace(0, np.nan, inplace=True)
df.interpolate(method='linear', inplace=True)
df.bfill(inplace=True)
df.ffill(inplace=True)

markersPosX = df.iloc[:, 0::3].values
markersPosZ = df.iloc[:, 1::3].values
markersPosY = df.iloc[:, 2::3].values
markers_names = [col[:-1] for col in df.iloc[:, 0::3].columns]

pos_tensor = np.stack([markersPosX, markersPosY, markersPosZ], axis=-1)
vel_tensor = np.zeros_like(pos_tensor)
vel_tensor[1:] = (pos_tensor[1:] - pos_tensor[:-1]) * fps

N_frames, N_joints, N_dims = pos_tensor.shape

# Identify joint indices
left_wrist_idx = markers_names.index("Leftwrist") if "Leftwrist" in markers_names else 0
right_wrist_idx = markers_names.index("Rightwrist") if "Rightwrist" in markers_names else 1
neck_idx = markers_names.index("Neck") if "Neck" in markers_names else 2

# ==========================================
# 2. INITIALIZE WINDOWS & FEATURES
# ==========================================
# We need specific window shapes for these primitives
sw_pos_full = SlidingWindow(max_length=sliding_window_len, n_signals=N_joints, n_dims=3)
sw_pos_single = SlidingWindow(max_length=sliding_window_len, n_signals=1, n_dims=3)
sw_speed_single = SlidingWindow(max_length=sliding_window_len, n_signals=1, n_dims=1)
sw_speed_pair = SlidingWindow(max_length=sliding_window_len, n_signals=2, n_dims=1)

features = {
    "sym": GeometricSymmetry(joint_pairs=[(left_wrist_idx, right_wrist_idx)], center_of_symmetry=neck_idx),
    "clust": Clusterability(n_neighbors=2),
    "rare": Rarity(alpha=0.5),

    # UPDATED: Uses Strategy 2 API to limit computations
    "stats": StatisticalMoment(methods=["mean", "std_dev"]),

    "sync": Synchronization(filter_params=None)
}

all_results = []

# ==========================================
# 3. REAL-TIME SIMULATION LOOP
# ==========================================
print("Running analysis primitives...")
for frame_idx in range(N_frames):
    # Extract specific data slices
    full_pos = pos_tensor[frame_idx]
    right_wrist_pos = pos_tensor[frame_idx, right_wrist_idx, :]

    left_wrist_speed = np.linalg.norm(vel_tensor[frame_idx, left_wrist_idx, :])
    right_wrist_speed = np.linalg.norm(vel_tensor[frame_idx, right_wrist_idx, :])

    # Update Windows
    sw_pos_full.append(full_pos)
    sw_pos_single.append([right_wrist_pos])
    sw_speed_single.append([[right_wrist_speed]])
    sw_speed_pair.append([[left_wrist_speed], [right_wrist_speed]])

    # Compute Features & Flatten
    frame_results = {}

    frame_results.update(features["sym"](sw_pos_full).to_flat_dict("sym"))
    frame_results.update(features["clust"](sw_pos_single).to_flat_dict("clust"))
    frame_results.update(features["rare"](sw_speed_single).to_flat_dict("rare"))
    frame_results.update(features["stats"](sw_speed_single).to_flat_dict("stats"))
    frame_results.update(features["sync"](sw_speed_pair).to_flat_dict("sync"))

    all_results.append(frame_results)

# ==========================================
# 4. VISUALIZATION
# ==========================================
print("Plotting results...")
results_df = pd.DataFrame(all_results)

# We will plot one key metric from each primitive
metrics_to_plot = [
    f"sym_pair_{left_wrist_idx}_{right_wrist_idx}",
    "clust_clusterability",
    "rare_rarity",
    "sync_plv",
    "stats_std_dev_0",  # Standard deviation of X coordinate
    "stats_mean_1"  # Mean of Y coordinate
]

fig, axes = plt.subplots(3, 2, figsize=(16, 10), sharex=True)
fig.suptitle("PyEyesWeb Analysis Primitives Overview", fontsize=16)

axes = axes.flatten()
for idx, metric in enumerate(metrics_to_plot):
    if metric in results_df.columns:
        # Drop None/NaN values for clean plotting
        valid_data = results_df[metric].dropna()
        axes[idx].plot(valid_data.index, valid_data, label=metric, color=f"C{idx + 2}")
        axes[idx].set_title(metric)
        axes[idx].grid(True, linestyle="--", alpha=0.6)
        axes[idx].legend(loc="upper right")
    else:
        axes[idx].text(0.5, 0.5, f"{metric} not computed", ha='center')

plt.tight_layout()
plt.subplots_adjust(top=0.92)
plt.savefig("primitives_validation_plot.png", dpi=150)
plt.show()