from pathlib import Path

import numpy as np
from tqdm import tqdm

# Import both loaders
from utils.data_loader import load_benchmark_data, load_smoothed_benchmark_data
from utils.animator import BenchmarkAnimator
from pyeyesweb.data_models.sliding_window import SlidingWindow
from pyeyesweb.analysis_primitives.rarity import Rarity

# 1. Configuration
data_type = "qualisys"  # Change to "kinect" to use the smoothed loader
tsv_file = "data/trial0001_impulsive.tsv"
bones_file = "data/bones_from_names.txt"
window_lengths = [50, 100, 150]

# Adjust joint names depending on your tracking system
joint_names = ["HAND_RIGHT", "HAND_LEFT"] if data_type == "qualisys" else ["Rightwrist", "Leftwrist"]

# 2. Load Data using the chosen pipeline
if data_type == "qualisys":
    pos_tensor, vel_tensor, marker_names, bones_edges = load_benchmark_data(tsv_file, bones_file)
else:
    pos_tensor, vel_tensor, marker_names, bones_edges = load_smoothed_benchmark_data(tsv_file, bones_file)

N_frames = pos_tensor.shape[0]

# 3. Compute Features
print("Computing Rarity features...")
rarity_feature = Rarity(alpha=0.5)

# Build feature dictionary for animator
feature_dict = {}

for w in window_lengths:
    subplot_title = f"Rarity (Window = {w})"
    feature_dict[subplot_title] = {}

    for joint in joint_names:
        if joint not in marker_names:
            print(f"Skipping {joint}, not found in marker list.")
            continue

        joint_idx = marker_names.index(joint)
        sw_speed = SlidingWindow(max_length=w, n_signals=1, n_dims=1)
        results = np.zeros(N_frames)

        for frame in tqdm(range(N_frames), desc=f"Processing {joint} (w={w})"):
            speed = np.linalg.norm(vel_tensor[frame, joint_idx, :])
            sw_speed.append([[speed]])

            # Using the streaming __call__ API
            res = rarity_feature(sw_speed)
            results[frame] = res.rarity if res.is_valid else 0.0

        feature_dict[subplot_title][joint] = results

# 4. Animate & Save!
animator = BenchmarkAnimator(
    pos_tensor=pos_tensor,
    feature_dict=feature_dict,
    marker_names=marker_names,
    bones_edges=bones_edges,
    title=f"Speed Rarity Analysis ({data_type.capitalize()})"
)

# Dynamically generate a clean save path (e.g., "result_trial0001_impulsive_Rarity.mp4")
file_stem = Path(tsv_file).stem
output_filename = f"result_{file_stem}_Rarity_{data_type}.mp4"

# Pass the save path into the show method
animator.show(save_path=output_filename)