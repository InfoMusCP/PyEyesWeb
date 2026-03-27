import pandas as pd
import numpy as np
import json
from io import StringIO
from pathlib import Path
from typing import Tuple, List, Dict, Optional


def _compute_kinematics(
    pos_tensor: np.ndarray, fps: float
) -> Tuple[np.ndarray, np.ndarray]:
    """Compute velocity and acceleration using vectorized NumPy differentiation."""
    vel_tensor = np.zeros_like(pos_tensor)
    vel_tensor[1:] = np.diff(pos_tensor, axis=0) * fps

    acc_tensor = np.zeros_like(vel_tensor)
    acc_tensor[1:] = np.diff(vel_tensor, axis=0) * fps

    return vel_tensor, acc_tensor


class GestureDataLoader:
    def __init__(self, data_dir: Path | str):
        self.data_dir = Path(data_dir)
        self.mappings_file = self.data_dir / "markers_mappings.json"

        self.mappings: Dict[str, List[str]] = {}
        if self.mappings_file.exists():
            with self.mappings_file.open("r") as f:
                self.mappings = json.load(f)

    def load(
        self,
        trial_name: str,
        sensor: str,
        standardize: bool = False,
        fps: float = 100.0,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, List[str]]:
        """Loads data from a specific sensor. Automatically appends .tsv if missing."""
        if not trial_name.endswith(".tsv"):
            trial_name += ".tsv"

        file_path = self.data_dir / sensor / trial_name
        if not file_path.exists():
            raise FileNotFoundError(
                f"Cannot find motion capture data at {file_path.resolve()}"
            )

        pos_tensor, marker_names = self._load_tsv(file_path)

        if standardize:
            if not self.mappings:
                print(
                    "Warning: standardize=True but markers_mappings.json not found. Returning original data."
                )
            else:
                pos_tensor, marker_names = self._standardize_data(
                    pos_tensor, marker_names
                )

        vel_tensor, acc_tensor = _compute_kinematics(pos_tensor, fps)

        return pos_tensor, vel_tensor, acc_tensor, marker_names

    def _load_tsv(self, path: Path) -> Tuple[np.ndarray, List[str]]:
        with path.open("r") as f:
            lines = f.readlines()

        # Find the header row
        data_start_idx = next(
            i for i, line in enumerate(lines) if line.startswith("Frame")
        )
        header = lines[data_start_idx].strip().split("\t")

        # Parse into Pandas, skipping text metadata
        df = pd.read_csv(
            StringIO("".join(lines[data_start_idx + 1 :])), sep="\t", names=header
        )

        # Method chaining for clean Pandas transformations
        df = df.replace(0, np.nan).interpolate(method="linear").ffill().bfill()

        # Safely extract X, Y, Z coordinates regardless of earlier inner columns
        # (like 'Frame', 'Time', 'SomeOtherMeta')
        x_cols = [c for c in df.columns if str(c).endswith(" X")]
        y_cols = [c for c in df.columns if str(c).endswith(" Y")]
        z_cols = [c for c in df.columns if str(c).endswith(" Z")]

        markers_names = [str(col)[:-2].strip() for col in x_cols]

        markers_x = df[x_cols].values
        markers_y = df[y_cols].values
        markers_z = df[z_cols].values

        # Stack into our standard 3D tensor
        pos_tensor = np.stack([markers_x, markers_y, markers_z], axis=-1)

        return pos_tensor, markers_names

    def _standardize_data(
        self, pos_tensor: np.ndarray, marker_names: List[str]
    ) -> Tuple[np.ndarray, List[str]]:
        """Standardizes markers according to markers_mappings.json by averaging them."""
        num_frames = pos_tensor.shape[0]
        dims = pos_tensor.shape[2]

        std_pos_tensor = []
        std_marker_names = []

        # Build reverse lookup for existing marker indices
        marker_idx_map = {name: idx for idx, name in enumerate(marker_names)}

        for std_name, aliases in self.mappings.items():
            valid_indices = [
                marker_idx_map[alias] for alias in aliases if alias in marker_idx_map
            ]

            if not valid_indices:
                # If sensor lacks this generic joint entirely, fill with NaNs (or zeros)
                std_pos_tensor.append(np.zeros((num_frames, dims)))
            else:
                # Compute the average positions of all valid matching markers
                mean_pos = np.mean(pos_tensor[:, valid_indices, :], axis=1)
                std_pos_tensor.append(mean_pos)

            std_marker_names.append(std_name)

        std_pos_tensor = np.stack(std_pos_tensor, axis=1)
        return std_pos_tensor, std_marker_names


# For backwards compatibility with older notebooks temporarily
def load_qualisys_tsv(
    file_path: Path | str, fps: float = 100.0
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, List[str]]:
    path = Path(file_path)
    loader = GestureDataLoader(path.parent)
    try:
        loader.data_dir = path.parent
        pos, names = loader._load_tsv(path)
        vel, acc = _compute_kinematics(pos, fps)
        return pos, vel, acc, names
    except Exception as e:
        raise e
