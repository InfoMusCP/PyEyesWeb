from pathlib import Path

import numpy as np
from tqdm import tqdm

# Import loaders and animator
from utils.data_loader import QualisysLoader, KinectLoader
from utils.animator import BenchmarkAnimator
from pyeyesweb.data_models.sliding_window import SlidingWindow

# The Feature
from pyeyesweb.analysis_primitives.synchronization import Synchronization

# ==========================================
# 1. SETUP & CONFIGURATION
# ==========================================
data_type = "kinect"  # Change to "kinect" to use the smoothed loader
tsv_file = "data/trial00007.txt"  # Adjust extension based on your data (.tsv or .txt)
bones_file = "data/bones_from_names.txt"

# Defined multiscale window lengths
window_lengths = [15, 30, 60]

# Adjust joint names depending on your tracking system
if data_type == "qualisys":
    joint_l, joint_r = "HAND_LEFT", "HAND_RIGHT"
else:
    joint_l, joint_r = "Leftwrist", "Rightwrist"

# ==========================================
# 2. LOAD DATA
# ==========================================
if data_type == "qualisys":
    loader = QualisysLoader()
else:
    # You can cleanly override smoothing parameters here
    loader = KinectLoader(rolling_window=5, savgol_len=70)

pos_tensor, vel_tensor, marker_names, bones_edges = loader.load(tsv_file, bones_file, fps=100.0)

N_frames = pos_tensor.shape[0]

# Locate the specific joints in the marker list
if joint_l not in marker_names or joint_r not in marker_names:
    raise ValueError(f"Could not find both {joint_l} and {joint_r} in the tracked markers.")

idx_l = marker_names.index(joint_l)
idx_r = marker_names.index(joint_r)

# ==========================================
# 3. INITIALIZE FEATURE & COMPUTE
# ==========================================
print(f"Computing Synchronization between {joint_l} and {joint_r}...")
synchronization_feature = Synchronization()

# Build feature dictionary for animator
feature_dict = {}

for w in window_lengths:
    subplot_title = f"Synchronization (Window = {w})"
    feature_dict[subplot_title] = {}

    # We configure the window to expect exactly 2 signals of 1 dimension each (speed)
    sw = SlidingWindow(max_length=w, n_signals=2, n_dims=1)
    results = np.zeros(N_frames)

    for frame in tqdm(range(N_frames), desc=f"Processing Window={w}"):
        # Extract the 1D speed (velocity magnitude) for both wrists
        speed_l = np.linalg.norm(vel_tensor[frame, idx_l, :])
        speed_r = np.linalg.norm(vel_tensor[frame, idx_r, :])

        # Append BOTH signals to the window simultaneously
        # Shape: (2 signals, 1 dimension) -> [[val1], [val2]]
        sw.append([[speed_l], [speed_r]])

        # Compute using the streaming __call__ API
        res = synchronization_feature(sw)

        # Safely extract the Phase Locking Value (PLV)
        results[frame] = res.plv if res.is_valid else 0.0

    # Store the computed array in the dictionary for the animator
    feature_dict[subplot_title][f"{joint_l} vs {joint_r} (PLV)"] = results

# ==========================================
# 4. RENDER & SAVE ANIMATION
# ==========================================
animator = BenchmarkAnimator(
    pos_tensor=pos_tensor,
    feature_dict=feature_dict,
    marker_names=marker_names,
    bones_edges=bones_edges,
    title=f"Multiscale Synchronization ({data_type.capitalize()})"
)

# Dynamically generate a clean save path
file_stem = Path(tsv_file).stem
output_filename = f"result_{file_stem}_Synchronization_{data_type}.mp4"

# Ensure results directory exists
Path("results").mkdir(exist_ok=True)

# Use the upgraded save_video method with the built-in progress bar!
print(f"Starting animation save to: results/{output_filename}")
animator.save_video(save_path=f"results/{output_filename}", video_fps=30)

# Optional: If you want to interact live after the video renders:
# animator.show()