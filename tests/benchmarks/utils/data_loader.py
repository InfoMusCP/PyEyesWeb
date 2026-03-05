from abc import ABC, abstractmethod
from io import StringIO
import pandas as pd
import numpy as np
from scipy.signal import savgol_filter
import ast


class BaseMocapLoader(ABC):
    """Abstract base class defining the standard loading pipeline for any MoCap sensor."""

    def load(self, tsv_path: str, bones_path: str = None, fps: float = 100.0):
        """The Master Pipeline. This dictates the order of operations."""
        print(f"Reading file: {tsv_path}")
        df = self._read_file(tsv_path)

        print("Cleaning missing values...")
        df = self._clean_missing_values(df)

        print("Extracting and sorting marker axes...")
        dfX, dfY, dfZ, marker_names = self._extract_markers(df)

        print("Building position tensor...")
        pos_tensor = self._build_position_tensor(dfX, dfY, dfZ)

        print("Computing Kinematics (Velocity)...")
        vel_tensor = self._compute_velocity(pos_tensor, fps)

        print("Parsing skeleton bones...")
        bones_edges = self._parse_bones(bones_path, marker_names)

        return pos_tensor, vel_tensor, marker_names, bones_edges

    # ==========================================
    # ABSTRACT METHODS (To be defined by subclasses)
    # ==========================================
    @abstractmethod
    def _read_file(self, path: str) -> pd.DataFrame:
        pass

    @abstractmethod
    def _extract_markers(self, df: pd.DataFrame) -> tuple:
        pass

    @abstractmethod
    def _build_position_tensor(self, dfX: pd.DataFrame, dfY: pd.DataFrame, dfZ: pd.DataFrame) -> np.ndarray:
        pass

    # ==========================================
    # SHARED METHODS (Write once, use everywhere)
    # ==========================================
    def _clean_missing_values(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df.replace(0, np.nan, inplace=True)
        df.interpolate(method='linear', inplace=True)
        df.ffill(inplace=True)
        df.bfill(inplace=True)
        return df

    def _extract_and_sort_axes(self, df: pd.DataFrame, name_cleaner_func) -> tuple:
        dfX = df.iloc[:, 0::3].rename(columns=name_cleaner_func)
        dfY = df.iloc[:, 1::3].rename(columns=name_cleaner_func)
        dfZ = df.iloc[:, 2::3].rename(columns=name_cleaner_func)

        dfX = dfX.reindex(sorted(dfX.columns), axis=1)
        dfY = dfY.reindex(sorted(dfY.columns), axis=1)
        dfZ = dfZ.reindex(sorted(dfZ.columns), axis=1)

        marker_names = list(dfX.columns)
        return dfX, dfY, dfZ, marker_names

    def _compute_velocity(self, pos_tensor: np.ndarray, fps: float) -> np.ndarray:
        vel_tensor = np.zeros_like(pos_tensor)
        vel_tensor[1:] = (pos_tensor[1:] - pos_tensor[:-1]) * fps
        return vel_tensor

    def _parse_bones(self, bones_path: str, marker_names: list) -> np.ndarray:
        bones_edges = []
        if bones_path:
            try:
                with open(bones_path, "r") as f:
                    bones_names = [ast.literal_eval(l.strip()) for l in f.readlines() if l.strip()]
                bones_edges = [[marker_names.index(b[0]), marker_names.index(b[1])]
                               for b in bones_names if b[0] in marker_names and b[1] in marker_names]
            except Exception as e:
                print(f"Warning: Skeleton not mapped properly. {e}")
        return np.array(bones_edges)


# ==========================================
# SENSOR-SPECIFIC IMPLEMENTATIONS
# ==========================================

class KinectLoader(BaseMocapLoader):
    """Loader specifically designed for Kinect TSV exports with smoothing and axis-swapping."""

    def __init__(self, rolling_window: int = 5, savgol_len: int = 70, savgol_poly: int = 3):
        self.rolling_window = rolling_window
        self.savgol_len = savgol_len
        self.savgol_poly = savgol_poly

    def _read_file(self, path: str) -> pd.DataFrame:
        # Kinect specific reading logic
        df = pd.read_csv(path, skiprows=4, sep='\t')
        cols_to_keep = [col for col in df.columns if (col.endswith("x") or col.endswith("y") or col.endswith("z"))
                        and "speed" not in col and "dist" not in col][2:]
        return df[cols_to_keep].drop_duplicates()

    def _extract_markers(self, df: pd.DataFrame) -> tuple:
        clean_func = lambda name: name.replace("out", "")[:-1]
        return self._extract_and_sort_axes(df, clean_func)

    def _build_position_tensor(self, dfX, dfY, dfZ) -> np.ndarray:
        print(f"Applying Savitzky-Golay smoothing (window={self.savgol_len}, poly={self.savgol_poly})...")

        def smooth(df_axis):
            return savgol_filter(
                df_axis.rolling(window=self.rolling_window, min_periods=1, center=True).mean().values,
                window_length=self.savgol_len, polyorder=self.savgol_poly, axis=0
            )

        posX = smooth(dfX)
        posY = smooth(dfY)
        posZ = smooth(dfZ)

        # Invert depth and swap axes for Kinect
        return np.stack([posX, -posZ, posY], axis=-1)


class QualisysLoader(BaseMocapLoader):
    """Loader specifically designed for raw Qualisys TSV exports."""

    def _read_file(self, path: str) -> pd.DataFrame:
        # EXACT Qualisys reading logic
        with open(path, 'r') as f:
            lines = f.readlines()

        data_start_idx = next(i for i, line in enumerate(lines) if line.startswith("Frame"))
        header = lines[data_start_idx].strip().split('\t')
        data_lines = lines[data_start_idx + 1:]

        df = pd.read_csv(StringIO(''.join(data_lines)), sep='\t', names=header)
        return df.iloc[:, 3:]

    def _extract_markers(self, df: pd.DataFrame) -> tuple:
        clean_func = lambda name: name[:-2].strip()
        return self._extract_and_sort_axes(df, clean_func)

    def _build_position_tensor(self, dfX, dfY, dfZ) -> np.ndarray:
        # Qualisys does not need smoothing or axis swapping.
        return np.stack([dfX.values, dfY.values, dfZ.values], axis=-1)