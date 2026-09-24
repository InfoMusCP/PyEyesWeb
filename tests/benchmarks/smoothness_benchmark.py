import sys
from pathlib import Path

# Add project root to python path to ensure we import the local package
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from tqdm import tqdm
from scipy.ndimage import median_filter

# Import loaders and animator
from utils.data_loader import QualisysLoader, KinectLoader
from utils.animator import BenchmarkAnimator
from pyeyesweb.data_models.sliding_window import SlidingWindow

# The Feature
from pyeyesweb.low_level.smoothness import Smoothness

# ==========================================
# 1. SETUP & CONFIGURATION
# ==========================================
# Loader mode: "qualisys" or "kinect"
data_type = "qualisys"  

# Path to the TSV file you want to analyze
tsv_file = r"C:\Users\simon\Desktop\Dati test smoothness\8.tsv"  

# Output options
save_csv = False          # Write frame-by-frame results to a CSV in results/
generate_plot = True     # Save static PNG plot of speed & metrics in results/
generate_video = False    # Render 3D animation video (requires ffmpeg, very slow)

# Resolve directories relative to the script location
script_dir = Path(__file__).resolve().parent
results_dir = script_dir / "results"
results_dir.mkdir(exist_ok=True)

# Convert tsv_file path to absolute path relative to the script dir if relative
tsv_path = Path(tsv_file)
if not tsv_path.is_absolute():
    tsv_path = script_dir / tsv_path

# Window lengths for sliding window feature computation (in frames)
window_lengths = [300]

# List of joint/marker names to analyze
joint_names = ["hand_right"]  # E.g., ["RWristOut", "RElbowOut"] or None for all

# Parameters for the Smoothness feature
rate_hz = 100.0
metrics_to_compute = [
    "sparc", 
    "ldlj_v", 
    "ldlj_a", 
    "jerk_rms", 
    "samp_en", 
    "harmonicity", 
    "n_submovements"
]
sparc_min_fc = 2.0
sparc_max_fc = 20.0
min_speed_threshold = 30.0  # mm/s: zero-velocity threshold for posture/rest

# ==========================================
# 2. HELPER FUNCTIONS
# ==========================================
def clean_and_smooth_series(arr: np.ndarray, window_size: int = 7) -> np.ndarray:
    """Interpolates NaN values due to zero-velocity and applies a light median filter."""
    series = pd.Series(arr)
    if series.dropna().empty:
        return np.zeros_like(arr)
    
    # Linear interpolation for NaNs, then backfill/forward fill boundaries
    series_interp = series.interpolate(method='linear').bfill().ffill()
    # Apply median filtering to smooth streaming window artifacts
    return median_filter(series_interp.values, size=window_size)

# ==========================================
# 3. LOAD DATA
# ==========================================
print(f"Loading data with {data_type} loader...")
if data_type == "qualisys":
    loader = QualisysLoader()
else:
    # KinectLoader applies Savitzky-Golay filtering and axis-swapping
    loader = KinectLoader(rolling_window=5, savgol_len=70)

pos_tensor, vel_tensor, marker_names, bones_edges = loader.load(
    str(tsv_path), None, fps=rate_hz
)

N_frames = pos_tensor.shape[0]
print(f"\nSuccessfully loaded {N_frames} frames.")
print(f"Available markers in file: {marker_names}")

# Resolve which joints to analyze
if not joint_names:
    joint_names = marker_names
    print(f"No specific joint_names provided. Automatically analyzing all {len(joint_names)} markers.")
else:
    print(f"Analyzing specified markers: {joint_names}")

# ==========================================
# 4. INITIALIZE FEATURE & COMPUTE
# ==========================================
print("\nInitializing Smoothness feature...")
smoothness_feature = Smoothness(
    rate_hz=rate_hz, 
    metrics=metrics_to_compute,
    sparc_min_fc=sparc_min_fc,
    sparc_max_fc=sparc_max_fc,
    min_speed_threshold=min_speed_threshold
)

feature_dict = {}
file_stem = tsv_path.stem

for w in window_lengths:
    subplot_title = f"Smoothness (Window = {w})"
    feature_dict[subplot_title] = {}

    csv_data = {
        "Frame": np.arange(N_frames),
        "Time": np.arange(N_frames) / rate_hz
    }

    for joint in joint_names:
        if joint not in marker_names:
            print(f"Skipping {joint}, not found in marker list.")
            continue

        joint_idx = marker_names.index(joint)

        # 1D Sliding window for speed (magnitude of velocity)
        sw_speed = SlidingWindow(max_length=w, n_signals=1, n_dims=1)
        
        # Raw output arrays for metrics
        speeds = np.zeros(N_frames)
        sparc_results = np.full(N_frames, np.nan)
        jerk_results = np.full(N_frames, np.nan)
        ldlj_v_results = np.full(N_frames, np.nan)
        ldlj_a_results = np.full(N_frames, np.nan)
        samp_en_results = np.full(N_frames, np.nan)
        harmonicity_results = np.full(N_frames, np.nan)
        n_sub_results = np.full(N_frames, np.nan)

        for frame in tqdm(range(N_frames), desc=f"Processing {joint} (w={w})"):
            # Extract speed for this specific joint
            speed = np.linalg.norm(vel_tensor[frame, joint_idx, :])
            speeds[frame] = speed
            sw_speed.append([[speed]])

            # Compute using the streaming __call__ API
            res = smoothness_feature(sw_speed)
            if res.is_valid:
                sparc_results[frame] = res.sparc if res.sparc is not None else np.nan
                jerk_results[frame] = res.jerk_rms if res.jerk_rms is not None else np.nan
                ldlj_v_results[frame] = res.ldlj_v if res.ldlj_v is not None else np.nan
                ldlj_a_results[frame] = res.ldlj_a if res.ldlj_a is not None else np.nan
                samp_en_results[frame] = res.samp_en if res.samp_en is not None else np.nan
                harmonicity_results[frame] = res.harmonicity if res.harmonicity is not None else np.nan
                n_sub_results[frame] = res.n_submovements if res.n_submovements is not None else np.nan


        

        # Clean & smooth for continuous visualization
        sparc_clean = clean_and_smooth_series(sparc_results,window_size=200)
        jerk_clean = clean_and_smooth_series(jerk_results)
        ldlj_v_clean = clean_and_smooth_series(ldlj_v_results)
        ldlj_a_clean = clean_and_smooth_series(ldlj_a_results)
        samp_en_clean = clean_and_smooth_series(samp_en_results)
        harmonicity_clean = clean_and_smooth_series(harmonicity_results)
        n_sub_clean = clean_and_smooth_series(n_sub_results)

        # Store SPARC for the 3D animator
        feature_dict[subplot_title][joint] = sparc_clean

        # Add to CSV dictionary
        csv_data[f"{joint}_Speed"] = speeds
        if "sparc" in metrics_to_compute:
            csv_data[f"{joint}_SPARC_w{w}"] = sparc_clean
        if "ldlj_v" in metrics_to_compute:
            csv_data[f"{joint}_LDLJ_V_w{w}"] = ldlj_v_clean
        if "ldlj_a" in metrics_to_compute:
            csv_data[f"{joint}_LDLJ_A_w{w}"] = ldlj_a_clean
        if "jerk_rms" in metrics_to_compute:
            csv_data[f"{joint}_JerkRMS_w{w}"] = jerk_clean
        if "samp_en" in metrics_to_compute:
            csv_data[f"{joint}_SampEn_w{w}"] = samp_en_clean
        if "harmonicity" in metrics_to_compute:
            csv_data[f"{joint}_Harmonicity_w{w}"] = harmonicity_clean
        if "n_submovements" in metrics_to_compute:
            csv_data[f"{joint}_N_Submovements_w{w}"] = n_sub_clean

        # Generate static PNG plot for this joint if enabled
        if generate_plot:
            print(f"Generating clean multi-metric plot for {joint}...")
            num_plots = 1 + len(metrics_to_compute)
            fig, axes = plt.subplots(num_plots, 1, figsize=(12, 2.3 * num_plots), sharex=True)
            
            # Plot Speed Profile
            axes[0].plot(csv_data["Time"], speeds, color="blue", linewidth=1.5)
            axes[0].set_title(f"Smoothness & Complexity Analysis for {joint} (File: {file_stem}, Window: {w})")
            axes[0].set_ylabel("Speed (mm/s)")
            axes[0].grid(True, linestyle="--", alpha=0.5)

            plot_idx = 1
            if "sparc" in metrics_to_compute:
                axes[plot_idx].plot(csv_data["Time"], sparc_clean, color="green", linewidth=1.5)
                axes[plot_idx].set_ylabel("SPARC\n(higher=smoother)")
                axes[plot_idx].grid(True, linestyle="--", alpha=0.5)
                plot_idx += 1

            if "ldlj_v" in metrics_to_compute:
                axes[plot_idx].plot(csv_data["Time"], ldlj_v_clean, color="orange", linewidth=1.5)
                axes[plot_idx].set_ylabel("LDLJ (Vel)\n(lower=smoother)")
                axes[plot_idx].grid(True, linestyle="--", alpha=0.5)
                plot_idx += 1

            if "ldlj_a" in metrics_to_compute:
                axes[plot_idx].plot(csv_data["Time"], ldlj_a_clean, color="purple", linewidth=1.5)
                axes[plot_idx].set_ylabel("LDLJ (Accel)\n(lower=smoother)")
                axes[plot_idx].grid(True, linestyle="--", alpha=0.5)
                plot_idx += 1

            if "jerk_rms" in metrics_to_compute:
                axes[plot_idx].plot(csv_data["Time"], jerk_clean, color="red", linewidth=1.5)
                axes[plot_idx].set_ylabel("Jerk RMS\n(lower=smoother)")
                axes[plot_idx].grid(True, linestyle="--", alpha=0.5)
                plot_idx += 1

            if "samp_en" in metrics_to_compute:
                axes[plot_idx].plot(csv_data["Time"], samp_en_clean, color="brown", linewidth=1.5)
                axes[plot_idx].set_ylabel("Sample Entropy\n(lower=regular)")
                axes[plot_idx].grid(True, linestyle="--", alpha=0.5)
                plot_idx += 1

            if "harmonicity" in metrics_to_compute:
                axes[plot_idx].plot(csv_data["Time"], harmonicity_clean, color="teal", linewidth=1.5)
                axes[plot_idx].set_ylabel("Harmonicity\n(1.0=harmonic)")
                axes[plot_idx].grid(True, linestyle="--", alpha=0.5)
                plot_idx += 1

            if "n_submovements" in metrics_to_compute:
                axes[plot_idx].plot(csv_data["Time"], n_sub_clean, color="magenta", linewidth=1.5)
                axes[plot_idx].set_ylabel("Submovements\n(lower=smoother)")
                axes[plot_idx].grid(True, linestyle="--", alpha=0.5)
                plot_idx += 1

            axes[-1].set_xlabel("Time (seconds)")
            plt.tight_layout()
            
            plot_path = results_dir / f"smoothness_plot_{file_stem}_{joint}_w{w}_full.png"
            plt.savefig(plot_path, dpi=150)
            plt.close()
            print(f"Saved plot to {plot_path}")

    # Save CSV if enabled
    if save_csv:
        df_results = pd.DataFrame(csv_data)
        csv_path = results_dir / f"smoothness_data_{file_stem}_w{w}.csv"
        df_results.to_csv(csv_path, index=False)
        print(f"\nSaved frame-by-frame data to {csv_path}")

# ==========================================
# 5. RENDER & SAVE ANIMATION (OPTIONAL)
# ==========================================
if generate_video:
    print("\nInitializing 3D Animator...")
    animator = BenchmarkAnimator(
        pos_tensor=pos_tensor,
        feature_dict=feature_dict,
        marker_names=marker_names,
        bones_edges=bones_edges,
        title=f"Smoothness Analysis ({data_type.capitalize()})",
    )

    output_filename = f"result_{file_stem}_Smoothness_{data_type}.gif"
    video_path = results_dir / output_filename
    
    animator.save_video(
        save_path=str(video_path),
        video_fps=30,
    )
    print(f"Saved 3D animation video to {video_path}")
else:
    print("\nSkipping 3D video generation (generate_video = True).")