import pandas as pd
import numpy as np
from io import StringIO
from pathlib import Path
from typing import Tuple


def _compute_kinematics(pos_tensor: np.ndarray, fps: float) -> Tuple[np.ndarray, np.ndarray]:
    """Compute velocity and acceleration using vectorized NumPy differentiation."""
    vel_tensor = np.zeros_like(pos_tensor)
    # np.diff is the Pythonic/SciPy standard for discrete differences
    vel_tensor[1:] = np.diff(pos_tensor, axis=0) * fps

    acc_tensor = np.zeros_like(vel_tensor)
    acc_tensor[1:] = np.diff(vel_tensor, axis=0) * fps

    return vel_tensor, acc_tensor


def load_qualisys_tsv(file_path: Path | str, fps: float = 100.0) -> Tuple[
    np.ndarray, np.ndarray, np.ndarray, list[str]]:
    """Loads and cleans Qualisys TSV data into (Time, Joints, Dims) tensors."""
    # Enforce pathlib for cross-platform safety
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Cannot find motion capture data at {path.resolve()}")

    with path.open('r') as f:
        lines = f.readlines()

    # Pythonic generator expression to find the header row
    data_start_idx = next(i for i, line in enumerate(lines) if line.startswith("Frame"))
    header = lines[data_start_idx].strip().split('\t')

    # Parse into Pandas, skipping text metadata
    df = pd.read_csv(StringIO(''.join(lines[data_start_idx + 1:])), sep='\t', names=header)
    df = df.iloc[:, 3:]  # Drop Frame/Time internal columns

    # Method chaining for clean Pandas transformations
    df = (df.replace(0, np.nan)
          .interpolate(method='linear')
          .ffill()
          .bfill())

    # Extract axes using Pandas slicing
    markers_x = df.iloc[:, 0::3]
    markers_y = df.iloc[:, 1::3]
    markers_z = df.iloc[:, 2::3]

    # Clean marker names (e.g., "HAND_RIGHT X" -> "HAND_RIGHT")
    markers_names = [col[:-2].strip() for col in markers_x.columns]

    # Stack into our standard 3D tensor
    pos_tensor = np.stack([markers_x.values, markers_y.values, markers_z.values], axis=-1)
    vel_tensor, acc_tensor = _compute_kinematics(pos_tensor, fps)

    return pos_tensor, vel_tensor, acc_tensor, markers_names
