import numpy as np
from tqdm import tqdm
from pathlib import Path

# Import both loaders
from utils.data_loader import load_benchmark_data, load_smoothed_benchmark_data
from utils.animator import BenchmarkAnimator
from pyeyesweb.low_level.contraction_expansion import (
    BoundingBoxFilledArea,
    EllipsoidSphericity,
    PointsDensity
)

# 1. Configuration
data_type = "kinect"  # Set to "kinect" to use the smoothed loader
tsv_file = "data/trial00005.txt" # Or .txt depending on your Kinect file
bones_file = "data/bones_from_names.txt"

# 2. Load Data using the chosen pipeline
if data_type == "qualisys":
    pos_tensor, _, marker_names, bones_edges = load_benchmark_data(tsv_file, bones_file)
else:
    pos_tensor, _, marker_names, bones_edges = load_smoothed_benchmark_data(tsv_file, bones_file)

N_frames = pos_tensor.shape[0]

# 3. Setup Features
print("Computing Static Posture features...")
feat_bb = BoundingBoxFilledArea()
feat_sph = EllipsoidSphericity()
feat_den = PointsDensity()

# Arrays to hold results
arr_bb = np.zeros(N_frames)
arr_sph = np.zeros(N_frames)
arr_den = np.zeros(N_frames)

# 4. Compute Loop (Using the ultra-fast Pure Math API)
for frame in tqdm(range(N_frames), desc="Evaluating Geometry"):
    frame_data = pos_tensor[frame]  # Shape: (N_joints, 3)

    # Bypass SlidingWindow entirely for raw array processing!
    res_bb = feat_bb.compute(frame_data)
    res_sph = feat_sph.compute(frame_data)
    res_den = feat_den.compute(frame_data)

    arr_bb[frame] = res_bb.contraction_index if res_bb.is_valid else 0.0
    arr_sph[frame] = res_sph.sphericity if res_sph.is_valid else 0.0
    arr_den[frame] = res_den.points_density if res_den.is_valid else 0.0

# 5. Format for Animator
# We create 3 separate subplots, each tracking the "Whole Body"
feature_dict = {
    "Contraction Index (Convex Hull / AABB)": {"Whole Body": arr_bb},
    "Ellipsoid Sphericity": {"Whole Body": arr_sph},
    "Points Density (Dispersion)": {"Whole Body": arr_den}
}

# 6. Animate & Save!
animator = BenchmarkAnimator(
    pos_tensor=pos_tensor,
    feature_dict=feature_dict,
    marker_names=marker_names,
    bones_edges=bones_edges,
    title=f"Contraction and Expansion Benchmark ({data_type.capitalize()})"
)

# Dynamically generate a clean save path (e.g., "result_trial0001_impulsive_Contraction_kinect.mp4")
file_stem = Path(tsv_file).stem
output_filename = f"result_{file_stem}_Contraction_{data_type}.mp4"

# Pass the save path into the show method to render the video
print(f"Starting animation save to: {output_filename}")
animator.save_video(save_path=output_filename, video_fps=30)