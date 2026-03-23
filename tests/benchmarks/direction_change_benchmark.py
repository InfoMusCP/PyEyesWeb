import numpy as np
from tqdm import tqdm
from pathlib import Path

# Loaders and Animator
from utils.data_loader import QualisysLoader, KinectLoader
from utils.animator import BenchmarkAnimator
from pyeyesweb.data_models.sliding_window import SlidingWindow

# The Feature
from pyeyesweb.low_level.direction_change import DirectionChange

# ==========================================
# 1. SETUP & CONFIGURATION
# ==========================================
data_type = "kinect"  # Using Kinect data
tsv_file = "data/trial00007.txt"
bones_file = "data/bones_from_names.txt"

# Parameters to tune!
dc_window_len = 50
epsilon_val = 0.5
sat_area = 0.3
sat_slope = 0.09

# ==========================================
# 2. LOAD DATA
# ==========================================
if data_type == "qualisys":
    loader = QualisysLoader()
else:
    # You can even override smoothing parameters cleanly!
    loader = KinectLoader(rolling_window=5, savgol_len=70)

pos_tensor, vel_tensor, marker_names, bones_edges = loader.load(tsv_file, bones_file, fps=30.0)

N_frames = pos_tensor.shape[0]
N_joints = pos_tensor.shape[1]
N_dims = pos_tensor.shape[2]

# ==========================================
# 3. INITIALIZE FEATURE & WINDOW
# ==========================================
print(f"Configuring Direction Change (window={dc_window_len}, epsilon={epsilon_val})...")

feature_dc = DirectionChange(
    metrics=["cosine", "polygon"],
    epsilon=epsilon_val,
    saturation_area=sat_area,
    saturation_slope=sat_slope
)

# Direction Change operates on the 3D trajectory of the WHOLE body (or average of it)
# so the window needs to ingest all joints.
sw_pos = SlidingWindow(max_length=dc_window_len, n_signals=N_joints, n_dims=N_dims)

arr_cosine = np.zeros(N_frames)
arr_polygon = np.zeros(N_frames)

# ==========================================
# 4. COMPUTATION LOOP
# ==========================================
for frame in tqdm(range(N_frames), desc="Evaluating Direction Change", unit="frames"):
    # 1. Push the current 3D posture into the window
    sw_pos.append(pos_tensor[frame])

    # 2. Compute the feature (Streaming API)
    res_dc = feature_dc(sw_pos)

    # 3. Extract and store
    arr_cosine[frame] = res_dc.cosine if res_dc.is_valid else 0.0
    arr_polygon[frame] = res_dc.polygon if res_dc.is_valid else 0.0

# ==========================================
# 5. RENDER & SAVE ANIMATION
# ==========================================
feature_dict = {
    f"Direction Change (w={dc_window_len})": {
        "Cosine Similarity (1D)": arr_cosine,
        "Polygon Area (2D/3D Saturated)": arr_polygon
    }
}

animator = BenchmarkAnimator(
    pos_tensor=pos_tensor,
    feature_dict=feature_dict,
    marker_names=marker_names,
    bones_edges=bones_edges,
    title=f"Direction Change Benchmark ({data_type.capitalize()})"
)

# Dynamically generate a clean save path
file_stem = Path(tsv_file).stem
output_filename = f"result_{file_stem}_DirectionChange_{data_type}.mp4"

# Use the new save_video method which includes the tqdm progress bar!
animator.save_video(save_path=f"results/{output_filename}", video_fps=30)

# Optional: If you also want to interact with it live after saving, uncomment the line below:
# animator.show()