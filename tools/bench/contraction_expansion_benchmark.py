import numpy as np
from tqdm import tqdm
from pathlib import Path

# Import both loaders
from utils.data_loader import QualisysLoader, KinectLoader
from utils.animator import BenchmarkAnimator
from pyeyesweb.low_level import BoundingBoxFilledArea, EllipsoidSphericity

# 1. Configuration
data_type = "kinect"  # Set to "kinect" to use the smoothed loader
tsv_file = "data/trial00007.txt" # Or .txt depending on your Kinect file
bones_file = "data/bones_from_names.txt"

# 2. Load Data using the chosen pipeline
if data_type == "qualisys":
    loader = QualisysLoader()
else:
    # You can even override smoothing parameters cleanly!
    loader = KinectLoader(rolling_window=5, savgol_len=70)

pos_tensor, vel_tensor, marker_names, bones_edges = loader.load(tsv_file, bones_file, fps=30.0)
N_frames = pos_tensor.shape[0]

# 3. Setup Features
print("Computing Static Posture features...")
feat_bb = BoundingBoxFilledArea()
feat_sph = EllipsoidSphericity()

# Arrays to hold results
arr_bb = np.zeros(N_frames)
arr_sph = np.zeros(N_frames)

# 4. Compute Loop (Using the ultra-fast Pure Math API)
for frame in tqdm(range(N_frames), desc="Evaluating Geometry"):
    frame_data = pos_tensor[frame]  # Shape: (N_joints, 3)

    # Bypass SlidingWindow entirely for raw array processing!
    res_bb = feat_bb.compute(frame_data)
    res_sph = feat_sph.process_points(frame_data)

    arr_bb[frame] = res_bb.contraction_index if res_bb.ok else 0.0
    arr_sph[frame] = res_sph.axis_ratio if res_sph.ok else 0.0

# 5. Format for Animator
# We create 3 separate subplots, each tracking the "Whole Body"
feature_dict = {
    "Contraction Index (Convex Hull / AABB)": {"Whole Body": arr_bb},
    "Ellipsoid Axis Ratio (minor / major radius)": {"Whole Body": arr_sph},
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
animator.save_video(save_path=f"results/{output_filename}", video_fps=30)