import numpy as np
from tqdm import tqdm
from pathlib import Path

# Loaders and Animator
from utils.data_loader import load_benchmark_data, load_smoothed_benchmark_data
from utils.animator import BenchmarkAnimator
from pyeyesweb.data_models.sliding_window import SlidingWindow

# The Feature
from pyeyesweb.low_level.geometric_symmetry import GeometricSymmetry

# ==========================================
# 1. SETUP & CONFIGURATION
# ==========================================
data_type = "kinect"  # Set to "qualisys" if you switch datasets
tsv_file = "data/trial00005.txt"  # Using your Kinect text file
bones_file = "data/bones_from_names.txt"

# Feature Hyperparameters
window_len = 50  # 50 frames of temporal history for the symmetry evaluation

# Define the pairs and the center of symmetry using the EXACT names from your file!
if data_type == "qualisys":
    pair_names = [
        ("SHOULDER_LEFT", "SHOULDER_RIGHT"),
        ("ELBOW_LEFT", "ELBOW_RIGHT"),
        ("HAND_LEFT", "HAND_RIGHT")
    ]
    center_name = "SPINE_BASE"
else:
    # Mapped directly to your Kinect file header
    pair_names = [
        ("Shoulderl", "Shoulderr"),
        ("Elbowl", "Elbowr"),
        ("Leftwrist", "Rightwrist")
    ]
    # Since there is no "Spinebase", "Hip" acts as the center of symmetry
    center_name = "Hip"

# ==========================================
# 2. LOAD DATA & MAP INDICES
# ==========================================
if data_type == "qualisys":
    pos_tensor, _, marker_names, bones_edges = load_benchmark_data(tsv_file, bones_file)
else:
    pos_tensor, _, marker_names, bones_edges = load_smoothed_benchmark_data(tsv_file, bones_file)

N_frames, N_joints, N_dims = pos_tensor.shape

# Safely map strings to numeric indices
joint_pairs = []
for left_name, right_name in pair_names:
    if left_name in marker_names and right_name in marker_names:
        joint_pairs.append((marker_names.index(left_name), marker_names.index(right_name)))
    else:
        print(f"Warning: Pair ({left_name}, {right_name}) not found in marker list. Skipping.")

if center_name in marker_names:
    center_idx = marker_names.index(center_name)
else:
    print(f"Warning: Center '{center_name}' not found. Defaulting to algorithmic Center of Mass.")
    center_idx = None

if not joint_pairs:
    raise ValueError("No valid joint pairs found to compute symmetry.")

# ==========================================
# 3. INITIALIZE FEATURE & WINDOW
# ==========================================
print(f"Configuring Geometric Symmetry (window={window_len})...")
print(f"Center of Symmetry: {center_name} (Index {center_idx})")

feature_sym = GeometricSymmetry(
    joint_pairs=joint_pairs,
    center_of_symmetry=center_idx
)

# We feed the entire skeletal structure into the window
sw_pos = SlidingWindow(max_length=window_len, n_signals=N_joints, n_dims=N_dims)

# Dictionaries to store the continuous results for each pair
results_dict = {f"{l}_{r}": np.zeros(N_frames) for l, r in joint_pairs}

# ==========================================
# 4. COMPUTATION LOOP
# ==========================================
for frame in tqdm(range(N_frames), desc="Evaluating Symmetry", unit="frames"):

    # Push the current 3D posture of all joints into the window
    sw_pos.append(pos_tensor[frame])

    # Compute the feature (Streaming API)
    res_sym = feature_sym(sw_pos)

    # Extract and store results for each pair
    if res_sym.is_valid and res_sym.pairs is not None:
        for pair_key in results_dict.keys():
            results_dict[pair_key][frame] = res_sym.pairs.get(pair_key, 0.0)

# ==========================================
# 5. RENDER & SAVE ANIMATION
# ==========================================
# Build the dictionary for the animator to create 3 separate stacked subplots
feature_dict = {}
plot_titles = ["Shoulders Symmetry", "Elbows Symmetry", "Wrists Symmetry"]

for i, (l_idx, r_idx) in enumerate(joint_pairs):
    pair_key = f"{l_idx}_{r_idx}"
    title = plot_titles[i] if i < len(plot_titles) else f"Pair {l_idx}-{r_idx}"

    # We map the nice string names back for the line label (e.g., "Leftwrist vs Rightwrist")
    l_name = marker_names[l_idx]
    r_name = marker_names[r_idx]

    feature_dict[title] = {
        f"{l_name} vs {r_name}": results_dict[pair_key]
    }

animator = BenchmarkAnimator(
    pos_tensor=pos_tensor,
    feature_dict=feature_dict,
    marker_names=marker_names,
    bones_edges=bones_edges,
    title=f"Bilateral Geometric Symmetry Benchmark ({data_type.capitalize()})"
)

# Dynamically generate a clean save path
file_stem = Path(tsv_file).stem
output_filename = f"result_{file_stem}_GeometricSymmetry_{data_type}.mp4"

# Render and save the video using the tqdm-enabled method
animator.save_video(save_path=output_filename, video_fps=30)

# Optional: To interact live after saving, uncomment:
# animator.show()