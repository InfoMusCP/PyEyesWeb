import numpy as np
from tqdm import tqdm
from pathlib import Path

# Loaders and Animator
from utils.data_loader import QualisysLoader, KinectLoader
from utils.animator import BenchmarkAnimator

# The Feature
from pyeyesweb.low_level.geometric_symmetry import GeometricSymmetry

# ==========================================
# 1. SETUP & CONFIGURATION
# ==========================================
data_type = "kinect"
tsv_file = "data/trial00007.txt"
bones_file = "data/bones_from_names.txt"

if data_type == "qualisys":
    pair_names = [("SHOULDER_LEFT", "SHOULDER_RIGHT"), ("ELBOW_LEFT", "ELBOW_RIGHT"), ("HAND_LEFT", "HAND_RIGHT")]
    center_name = "SPINE_BASE"
    loader = QualisysLoader()
else:
    pair_names = [("Shoulderl", "Shoulderr"), ("Elbowl", "Elbowr"), ("Leftwrist", "Rightwrist")]
    center_name = "Hip"
    loader = KinectLoader(rolling_window=5, savgol_len=70)

pos_tensor, vel_tensor, marker_names, bones_edges = loader.load(tsv_file, bones_file, fps=30.0)
N_frames = pos_tensor.shape[0]

# Safely map strings to numeric indices
joint_pairs = []
for l_name, r_name in pair_names:
    if l_name in marker_names and r_name in marker_names:
        joint_pairs.append((marker_names.index(l_name), marker_names.index(r_name)))

center_idx = marker_names.index(center_name) if center_name in marker_names else None

# ==========================================
# 2. INITIALIZE FEATURE
# ==========================================
feature_sym = GeometricSymmetry(joint_pairs=joint_pairs, center_of_symmetry=center_idx)

# Dictionaries to store the continuous results for each pair
results_dict = {f"{l}_{r}": np.zeros(N_frames) for l, r in joint_pairs}

# ==========================================
# 3. FAST COMPUTATION LOOP (No Sliding Window!)
# ==========================================
for frame in tqdm(range(N_frames), desc="Evaluating Symmetry", unit="frames"):

    # Pass the raw 2D array directly to the Pure Math API
    res_sym = feature_sym.compute(pos_tensor[frame])

    if res_sym.is_valid and res_sym.pairs is not None:
        for pair_key in results_dict.keys():
            results_dict[pair_key][frame] = res_sym.pairs.get(pair_key, 0.0)

# ==========================================
# 4. RENDER & SAVE ANIMATION
# ==========================================
feature_dict = {}
plot_titles = ["Shoulders Symmetry", "Elbows Symmetry", "Wrists Symmetry"]

for i, (l_idx, r_idx) in enumerate(joint_pairs):
    title = plot_titles[i] if i < len(plot_titles) else f"Pair {l_idx}-{r_idx}"
    feature_dict[title] = {f"{marker_names[l_idx]} vs {marker_names[r_idx]}": results_dict[f"{l_idx}_{r_idx}"]}

animator = BenchmarkAnimator(
    pos_tensor=pos_tensor,
    feature_dict=feature_dict,
    marker_names=marker_names,
    bones_edges=bones_edges,
    title=f"Instantaneous Bilateral Symmetry ({data_type.capitalize()})"
)

output_filename = f"result_{Path(tsv_file).stem}_GeometricSymmetry_{data_type}.mp4"
animator.save_video(save_path=f"results/{output_filename}", video_fps=30)