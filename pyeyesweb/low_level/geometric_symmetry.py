"""Bilateral symmetry analysis module.

This module provides tools for quantifying the symmetry and synchronization
between bilateral body parts (e.g., left and right limbs) using multiple 
metrics including Bilateral Symmetry Index (BSI), Canonical Correlation 
Analysis (CCA), and Phase Synchronization.
"""

from dataclasses import dataclass
from typing import Dict, Optional, List, Tuple
import numpy as np

from pyeyesweb.data_models.base import DynamicFeature
from pyeyesweb.data_models.results import FeatureResult
from pyeyesweb.utils.validators import validate_pairs


@dataclass(slots=True)
class GeometricSymmetryResult(FeatureResult):
    """Output contract for Geometric Symmetry."""
    pairs: Optional[Dict[str, float]] = None

    def to_flat_dict(self, prefix: str = "") -> Dict[str, float]:
        """Dynamically unrolls the dictionary of joint pairs into flat scalars."""
        # Evade the Python 3.10 super() slots bug
        flat = FeatureResult.to_flat_dict(self, prefix)

        def make_key(base: str, sub: str) -> str:
            return f"{prefix}_{base}_{sub}" if prefix else f"{base}_{sub}"

        # Unroll the pairs dictionary (e.g., {"0_1": 0.85} -> pair_0_1: 0.85)
        pairs_dict = flat.pop(f"{prefix}_pairs" if prefix else "pairs", None)
        if pairs_dict is not None:
            for pair_key, val in pairs_dict.items():
                flat[make_key("pair", pair_key)] = float(val)

        return flat


class GeometricSymmetry(DynamicFeature):
    """
    Computes the spatial symmetry error for a sequence of skeletal frames.

    The symmetry is calculated by reflecting joints across a central plane
    passing through the 'center of symmetry' and measuring the deviation
    over the entire sliding window.
    """

    def __init__(self, joint_pairs: List[Tuple[int, int]], center_of_symmetry: Optional[int] = None):
        """
        Args:
            joint_pairs (list of tuples): List of (left_joint_idx, right_joint_idx).
            center_of_symmetry (int, optional): Index of the joint representing the center
                                       (e.g., pelvis). If None, the center of mass
                                       per frame is used.
        """
        super().__init__()
        self._center_idx = center_of_symmetry if center_of_symmetry is not None else -1
        self._signal_pairs = set(validate_pairs(joint_pairs))

        if not self._signal_pairs:
            raise ValueError("At least one signal pair must be provided.")

        # Max index check for validation
        self._max_required_idx = max(max(pair) for pair in self._signal_pairs)
        if self._center_idx != -1:
            self._max_required_idx = max(self._max_required_idx, self._center_idx)

    def compute(self, window_data: np.ndarray) -> GeometricSymmetryResult:
        """
        Expects window_data as a 3D tensor: (Time, N_signals, N_dims).
        """
        t, m, n = window_data.shape

        # 1. Validation Fail-Safe
        if m <= self._max_required_idx:
            return GeometricSymmetryResult(is_valid=False)

        # 2. Determine the Center of Symmetry (CoS)
        if self._center_idx != -1:
            # Extract specific signal and keep dims for broadcasting: (Time, 1, Dims)
            cos = window_data[:, self._center_idx, :][:, np.newaxis, :]
        else:
            # Calculate Center of Mass (Mean of all signals): (Time, 1, Dims)
            cos = np.mean(window_data, axis=1)[:, np.newaxis, :]

        # 3. Center the data
        centered_data = window_data - cos

        # 4. Compute Symmetry Error
        pair_errors = {}
        for left_idx, right_idx in self._signal_pairs:
            left_joints = centered_data[:, left_idx, :]   # Shape: (Time, 3)
            right_joints = centered_data[:, right_idx, :] # Shape: (Time, 3)

            # Reflect the right joint across the X-axis (index 0)
            reflected_right = right_joints.copy()
            reflected_right[:, 0] = -reflected_right[:, 0]

            # Calculate mean Euclidean distance between Left and Reflected Right over time
            mean_error = np.mean(np.linalg.norm(left_joints - reflected_right, axis=1))

            # Create a clean string key for the flat dictionary (e.g., "0_1")
            pair_key = f"{left_idx}_{right_idx}"
            pair_errors[pair_key] = float(1.0 - mean_error)

        return GeometricSymmetryResult(pairs=pair_errors)
