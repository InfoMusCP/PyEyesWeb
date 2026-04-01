"""Barycenter and equilibrium analysis for postural snapshots.

This module provides features for analysing postural balance. It computes the
relationship between two support points (e.g. feet) and a barycenter to
estimate the stability of a movement.
"""

from dataclasses import dataclass
import numpy as np

from pyeyesweb.data_models.base import StaticFeature
from pyeyesweb.data_models.results import FeatureResult


@dataclass(slots=True)
class EquilibriumResult(FeatureResult):
    """Output contract for Elliptical Equilibrium evaluation.

    Attributes
    ----------
    value : float
        Scalar equilibrium value in `[0, 1]`. `1.0` indicates perfect
        centering; `0.0` indicates the barycenter is outside the support
        ellipse.
    angle : float
        Angle of the support vector in degrees.
    """
    value: float = 0.0
    angle: float = 0.0


class Equilibrium(StaticFeature):
    """Elliptical equilibrium evaluation between two feet and a barycenter.

    Computes how well the barycenter is centered between two support points
    using an elliptical model.

    !!! note
        This method relies on 2D projections of the 3D joints.

    Read more in the [User Guide](../../user_guide/theoretical_framework/low_level/postural_balance.md).

    Parameters
    ----------
    left_foot_idx : int, optional
        Index of the left support node. Defaults to `0`.
    right_foot_idx : int, optional
        Index of the right support node. Defaults to `1`.
    barycenter_idx : int, optional
        Index of the barycenter node. Defaults to `2`.
    margin_mm : float, optional
        Safety margin in millimeters added to the support ellipse.
        Defaults to `100.0`.
    y_weight : float, optional
        Weighting factor for the semi-minor axis of the ellipse.
        Defaults to `0.5`.
    axes : tuple of int, optional
        Indices of the axes to project onto the floor plane.
        Defaults to `(0, 1)` (X and Y). Use `(0, 2)` for X and Z.

    Examples
    --------
    >>> eq = Equilibrium(left_foot_idx=10, right_foot_idx=11, barycenter_idx=2)
    """

    EPSILON = 1e-10

    def __init__(
            self,
            left_foot_idx: int = 0,
            right_foot_idx: int = 1,
            barycenter_idx: int = 2,
            margin_mm: float = 100.0,
            y_weight: float = 0.5,
            axes: tuple[int, int] = (0, 1)
    ):
        super().__init__()  # Crucial for proper inheritance
        self.left_foot_idx = left_foot_idx
        self.right_foot_idx = right_foot_idx
        self.barycenter_idx = barycenter_idx
        self.margin = margin_mm
        self.y_weight = y_weight
        self.axes = axes

    @property
    def left_foot_idx(self) -> int:
        """Index of the left foot node."""
        return self._left_foot_idx

    @left_foot_idx.setter
    def left_foot_idx(self, value: int):
        self._left_foot_idx = int(value)

    @property
    def right_foot_idx(self) -> int:
        """Index of the right foot node."""
        return self._right_foot_idx

    @right_foot_idx.setter
    def right_foot_idx(self, value: int):
        self._right_foot_idx = int(value)

    @property
    def barycenter_idx(self) -> int:
        """Index of the barycenter node."""
        return self._barycenter_idx

    @barycenter_idx.setter
    def barycenter_idx(self, value: int):
        self._barycenter_idx = int(value)

    @property
    def margin(self) -> float:
        """Safety margin in millimeters."""
        return self._margin

    @margin.setter
    def margin(self, value: float):
        self._margin = float(value)

    @property
    def y_weight(self) -> float:
        """Weighting factor for the semi-minor axis."""
        return self._y_weight

    @y_weight.setter
    def y_weight(self, value: float):
        self._y_weight = float(value)

    @property
    def axes(self) -> tuple[int, int]:
        """Indices of the axes forming the support plane."""
        return self._axes

    @axes.setter
    def axes(self, value: tuple[int, int]):
        if len(value) != 2:
            raise ValueError("Axes must be a sequence of two integers.")
        self._axes = (int(value[0]), int(value[1]))
        self._axes_list = list(self._axes)

    def compute(self, frame_data: np.ndarray) -> EquilibriumResult:
        """Compute the elliptical equilibrium score.

        Parameters
        ----------
        frame_data : numpy.ndarray
            Snapshot of joint positions of shape (N_signals, N_dims).

        Returns
        -------
        EquilibriumResult
            Result containing the equilibrium value and support angle.
        """
        # 1. Robustness: Ensure we have enough joints in the frame
        max_idx = max(self.left_foot_idx, self.right_foot_idx, self.barycenter_idx)
        if len(frame_data) <= max_idx:
            # Replaced arbitrary zeros with a standardized invalid flag
            return EquilibriumResult(is_valid=False)

        # 2. Extract 2D positions
        p_left = frame_data[self.left_foot_idx][self._axes_list]
        p_right = frame_data[self.right_foot_idx][self._axes_list]
        p_barycenter = frame_data[self.barycenter_idx][self._axes_list]

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