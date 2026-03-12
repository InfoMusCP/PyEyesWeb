from dataclasses import dataclass
import numpy as np

from pyeyesweb.data_models.base import StaticFeature
from pyeyesweb.data_models.results import FeatureResult


@dataclass(slots=True)
class EquilibriumResult(FeatureResult):
    """Output contract for Elliptical Equilibrium evaluation."""
    value: float = 0.0
    angle: float = 0.0


class Equilibrium(StaticFeature):
    """Elliptical equilibrium evaluation between two feet and a barycenter."""

    EPSILON = 1e-10

    def __init__(
            self,
            left_foot_idx: int = 0,
            right_foot_idx: int = 1,
            barycenter_idx: int = 2,
            margin_mm: float = 100.0,
            y_weight: float = 0.5
    ):
        super().__init__()  # Crucial for proper inheritance
        self.left_foot_idx = left_foot_idx
        self.right_foot_idx = right_foot_idx
        self.barycenter_idx = barycenter_idx
        self.margin = margin_mm
        self.y_weight = y_weight

    @property
    def left_foot_idx(self) -> int:
        return self._left_foot_idx

    @left_foot_idx.setter
    def left_foot_idx(self, value: int):
        self._left_foot_idx = int(value)

    @property
    def right_foot_idx(self) -> int:
        return self._right_foot_idx

    @right_foot_idx.setter
    def right_foot_idx(self, value: int):
        self._right_foot_idx = int(value)

    @property
    def barycenter_idx(self) -> int:
        return self._barycenter_idx

    @barycenter_idx.setter
    def barycenter_idx(self, value: int):
        self._barycenter_idx = int(value)

    @property
    def margin(self) -> float:
        return self._margin

    @margin.setter
    def margin(self, value: float):
        self._margin = float(value)

    @property
    def y_weight(self) -> float:
        return self._y_weight

    @y_weight.setter
    def y_weight(self, value: float):
        self._y_weight = float(value)

    def compute(self, frame_data: np.ndarray) -> EquilibriumResult:
        # 1. Robustness: Ensure we have enough joints in the frame
        max_idx = max(self.left_foot_idx, self.right_foot_idx, self.barycenter_idx)
        if len(frame_data) <= max_idx:
            # Replaced arbitrary zeros with a standardized invalid flag
            return EquilibriumResult(is_valid=False)

        # 2. Extract 2D positions
        p_left = frame_data[self.left_foot_idx][:2]
        p_right = frame_data[self.right_foot_idx][:2]
        p_barycenter = frame_data[self.barycenter_idx][:2]

        # 3. Compute Rotation-Invariant Ellipse Geometry
        center = (p_left + p_right) / 2.0
        delta = p_right - p_left
        foot_distance = np.linalg.norm(delta)

        # Semi-major axis (a) is half the distance between feet + margin
        # Semi-minor axis (b) is scaled proportionally from the margin
        a = (foot_distance / 2.0) + self.margin
        b = self.margin * self.y_weight

        # 4. Rotation Matrix (Aligning relative barycenter to the feet vector)
        angle = np.arctan2(delta[1], delta[0])
        rel = p_barycenter - center

        # Pre-calculated trig values for speed
        cos_a, sin_a = np.cos(-angle), np.sin(-angle)
        rot_matrix = np.array([
            [cos_a, -sin_a],
            [sin_a, cos_a]
        ])

        rel_rot = rot_matrix @ rel

        # 5. Evaluate Equilibrium (Distance from center normalized by ellipse axes)
        value = 0.0

        if a < self.EPSILON and b < self.EPSILON:
            value = 1.0 if np.linalg.norm(rel) < self.EPSILON else 0.0
        elif a < self.EPSILON:
            if abs(rel_rot[0]) <= self.EPSILON:
                norm_y = (rel_rot[1] / b) ** 2
                value = 1.0 - np.sqrt(norm_y) if norm_y <= 1.0 else 0.0
        elif b < self.EPSILON:
            if abs(rel_rot[1]) <= self.EPSILON:
                norm_x = (rel_rot[0] / a) ** 2
                value = 1.0 - np.sqrt(norm_x) if norm_x <= 1.0 else 0.0
        else:
            norm = (rel_rot[0] / a) ** 2 + (rel_rot[1] / b) ** 2
            if norm <= 1.0:
                value = 1.0 - np.sqrt(norm)

        return EquilibriumResult(
            value=float(max(0.0, value)),
            angle=float(np.degrees(angle))
        )