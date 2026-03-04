from io import StringIO
import pandas as pd
import numpy as np
from scipy.signal import savgol_filter
import ast

def load_smoothed_benchmark_data(
        tsv_path: str,
        bones_path: str = None,
        fps: float = 100.0,
        rolling_window: int = 5,
        savgol_len: int = 70,
        savgol_poly: int = 3
):
    """Loads, cleans, and applies Savitzky-Golay smoothing (designed for Kinect data)."""
    print(f"Reading file: {tsv_path}")

    # Read the data, skipping the 4 header rows based on your notebook
    df = pd.read_csv(tsv_path, skiprows=4, sep='\t')

    # Filter columns to keep only coordinates, ignoring speed/dist metrics
    cols_to_keep = [col for col in df.columns if (col.endswith("x") or col.endswith("y") or col.endswith("z"))
                    and not "speed" in col and not "dist" in col][2:]
    df = df[cols_to_keep].drop_duplicates()

    print("Cleaning missing values...")
    df.replace(0, np.nan, inplace=True)
    df.interpolate(method='linear', inplace=True)
    df.ffill(inplace=True)
    df.bfill(inplace=True)

    # Extract axes
    markersPosTableX = df.iloc[:, 0::3]
    markersPosTableY = df.iloc[:, 1::3]  # Based on your notebook mapping
    markersPosTableZ = df.iloc[:, 2::3]

    # Clean names by removing "out" and sort alphabetically
    clean_name = lambda name: name.replace("out", "")
    markersPosTableX = markersPosTableX.rename(columns={c: clean_name(c) for c in markersPosTableX.columns})
    markersPosTableY = markersPosTableY.rename(columns={c: clean_name(c) for c in markersPosTableY.columns})
    markersPosTableZ = markersPosTableZ.rename(columns={c: clean_name(c) for c in markersPosTableZ.columns})

    markersPosTableX = markersPosTableX.reindex(sorted(markersPosTableX.columns), axis=1)
    markersPosTableY = markersPosTableY.reindex(sorted(markersPosTableY.columns), axis=1)
    markersPosTableZ = markersPosTableZ.reindex(sorted(markersPosTableZ.columns), axis=1)

    marker_names = [col[:-1] for col in markersPosTableX.columns]

    print(f"Applying Savitzky-Golay smoothing (window={savgol_len}, poly={savgol_poly})...")
    markersPosX = savgol_filter(
        markersPosTableX.rolling(window=rolling_window, min_periods=1, center=True).mean().values,
        window_length=savgol_len, polyorder=savgol_poly, axis=0)
    markersPosY = savgol_filter(
        markersPosTableY.rolling(window=rolling_window, min_periods=1, center=True).mean().values,
        window_length=savgol_len, polyorder=savgol_poly, axis=0)
    markersPosZ = savgol_filter(
        markersPosTableZ.rolling(window=rolling_window, min_periods=1, center=True).mean().values,
        window_length=savgol_len, polyorder=savgol_poly, axis=0)

    # Create Master Tensors
    pos_tensor = np.stack([markersPosX, markersPosY, markersPosZ], axis=-1)

    vel_tensor = np.zeros_like(pos_tensor)
    vel_tensor[1:] = (pos_tensor[1:] - pos_tensor[:-1]) * fps

    # Parse Bones
    bones_edges = []
    if bones_path:
        try:
            with open(bones_path, "r") as f:
                bones_names = [ast.literal_eval(l.strip()) for l in f.readlines() if l.strip()]
            bones_edges = [[marker_names.index(b[0]), marker_names.index(b[1])]
                           for b in bones_names if b[0] in marker_names and b[1] in marker_names]
        except Exception as e:
            print(f"Warning: Skeleton not mapped properly. {e}")

    return pos_tensor, vel_tensor, marker_names, np.array(bones_edges)


def load_benchmark_data(tsv_path: str, bones_path: str = None, fps: float = 100.0):
    """Loads and cleans Qualisys TSV data and bone hierarchies for benchmarking."""
    print(f"Reading file: {tsv_path}")
    with open(tsv_path, 'r') as f:
        lines = f.readlines()

    data_start_idx = next(i for i, line in enumerate(lines) if line.startswith("Frame"))
    header = lines[data_start_idx].strip().split('\t')
    data_lines = lines[data_start_idx + 1:]

    df = pd.read_csv(StringIO(''.join(data_lines)), sep='\t', names=header)
    df = df.iloc[:, 3:]

    print("Cleaning data...")
    df.replace(0, np.nan, inplace=True)
    df.interpolate(method='linear', inplace=True)
    df.ffill(inplace=True)
    df.bfill(inplace=True)

    # Extract marker position tables
    markersPosTableX = df.iloc[:, 0::3]
    markersPosTableY = df.iloc[:, 1::3]
    markersPosTableZ = df.iloc[:, 2::3]

    # Sort columns alphabetically by marker name
    markersPosTableX = markersPosTableX.reindex(sorted(markersPosTableX.columns), axis=1)
    markersPosTableY = markersPosTableY.reindex(sorted(markersPosTableY.columns), axis=1)
    markersPosTableZ = markersPosTableZ.reindex(sorted(markersPosTableZ.columns), axis=1)

    # Clean names
    clean_name = lambda name: name[:-2].strip()
    markersPosTableX = markersPosTableX.rename(columns={c: clean_name(c) for c in markersPosTableX})

    marker_names = list(markersPosTableX.columns)

    # Create Master Position Tensor
    pos_tensor = np.stack([markersPosTableX.values, markersPosTableY.values, markersPosTableZ.values], axis=-1)

    # Calculate Velocity
    print("Computing Kinematics (Velocity)...")
    vel_tensor = np.zeros_like(pos_tensor)
    vel_tensor[1:] = (pos_tensor[1:] - pos_tensor[:-1]) * fps

    # Parse Bones
    bones_edges = []
    if bones_path:
        try:
            with open(bones_path, "r") as f:
                bones_names = [ast.literal_eval(l.strip()) for l in f.readlines() if l.strip()]
            bones_edges = [[marker_names.index(b[0]), marker_names.index(b[1])]
                           for b in bones_names if b[0] in marker_names and b[1] in marker_names]
        except FileNotFoundError:
            print(f"Warning: {bones_path} not found. Using empty skeleton.")

    return pos_tensor, vel_tensor, marker_names, np.array(bones_edges)