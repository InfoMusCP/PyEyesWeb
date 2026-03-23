from dataclasses import dataclass
from typing import Literal, List, Optional
import numpy as np

from pyeyesweb.data_models.base import DynamicFeature
from pyeyesweb.data_models.results import FeatureResult
from pyeyesweb.utils.validators import validate_string


@dataclass(slots=True)
class DirectionChangeResult(FeatureResult):
    """Output contract for Direction Change.
    
    Attributes
    ----------
    cosine : float, optional
        The direction change evaluated using cosine similarity.
    polygon : float, optional
        The polygon area enclosed by the trajectory.
    """
    cosine: Optional[float] = None
    polygon: Optional[float] = None


class DirectionChange(DynamicFeature):
    """Direction Change evaluation based on movement vectors.

    !!! note
        Supports multiple metrics such as cosine similarity and polygon area.

    Read more in the [User Guide](../../user_guide/theoretical_framework/low_level/direction_change.md).

    Parameters
    ----------
    epsilon : float, optional
        Threshold parameter for the cosine metric. Defaults to `0.5`.
    num_subsamples : int, optional
        Number of subsamples used for polygon area calculation. Defaults to `20`.
    metrics : list of {'cosine', 'polygon'}, optional
        The metrics to compute. By default, computes all allowed metrics.
    """

    _ALLOWED_METRICS = ["cosine", "polygon"]

    def __init__(
            self,
            epsilon: float = 0.5,
            num_subsamples: int = 20,
            metrics: List[Literal["cosine", "polygon"]] = None
    ):
        super().__init__()
        self._epsilon = float(epsilon)
        self._num_subsamples = int(num_subsamples)
        self._metrics = metrics if metrics is not None else self._ALLOWED_METRICS

    @property
    def epsilon(self) -> float:
        return self._epsilon

    @epsilon.setter
    def epsilon(self, value: float):
        self._epsilon = float(value)

    @property
    def num_subsamples(self) -> int:
        return self._num_subsamples

    @num_subsamples.setter
    def num_subsamples(self, value: int):
        self._num_subsamples = int(value)

    @property
    def metrics(self) -> List[str]:
        return self._metrics

    @metrics.setter
    def metrics(self, value: Optional[List[str]]):
        target_metrics = value if value is not None else self._ALLOWED_METRICS
        self._metrics = [validate_string(m, self._ALLOWED_METRICS) for m in target_metrics]

    def _cosine_similarity(self, pos: np.ndarray) -> float:
        if pos.shape[-1] < 2:
            raise ValueError("Input positions must be at least 2D (x,y).")

        n_samples = pos.shape[0]
        if n_samples < 3:
            raise ValueError("Not enough samples")

        # Extract Start, Mid, and End points of the trajectory
        p0 = pos[-1]
        p1 = pos[n_samples // 2]
        p2 = pos[0]

        L0 = p0 - p1
        L1 = p1 - p2

        norm0 = np.linalg.norm(L0)
        norm1 = np.linalg.norm(L1)

        if norm0 < 1e-6 or norm1 < 1e-6:
            return 0.0

        dot = np.dot(L0, L1)
        cos_theta = np.clip(dot / (norm0 * norm1), -1.0, 1.0)
        theta = np.arccos(cos_theta)

        angle_norm = theta / np.pi
        a = 1.0 - angle_norm
        diff = np.abs(a - 0.5)

        if diff < self.epsilon:
            return float(1.0 - diff / self.epsilon)

        return 0.0

    def _polygon_area(self, pos: np.ndarray) -> float:
        num_points = len(pos)
        if num_points < 3:
            raise ValueError("Not enough samples")

        # Subsample the trajectory securely
        indices = np.linspace(0, num_points - 1, min(self.num_subsamples, num_points))
        subset = pos[np.round(indices).astype(int)]

        # Close the loop
        closed_polygon = np.vstack([subset, subset[0]])

        # Shoelace-style cross product area computation
        cross_products = np.cross(closed_polygon[:-1], closed_polygon[1:])
        area_vector = np.sum(cross_products, axis=0) / 2.0

        # Handle both 2D (scalar return) and 3D (vector return) area magnitudes
        area = np.linalg.norm(area_vector) if np.ndim(area_vector) > 0 else np.abs(area_vector)
        
        return float(area)

    def compute(self, window_data: np.ndarray) -> DirectionChangeResult:
        """Compute the Direction Change over a temporal window.

        Parameters
        ----------
        window_data : numpy.ndarray
            A 3D tensor of motion data within the sliding window.

        Returns
        -------
        DirectionChangeResult
            The computed direction change metrics.
        """
        if window_data.shape[0] < 3:
            return DirectionChangeResult(is_valid=False)

        # 1. Shared Preprocessing
        trajectory = np.mean(window_data, axis=1)

        # 2. Selective Execution
        val_cosine = None
        val_polygon = None

        try:
            if "cosine" in self.metrics:
                val_cosine = self._cosine_similarity(trajectory)

            if "polygon" in self.metrics:
                val_polygon = self._polygon_area(trajectory)

        except ValueError:
            return DirectionChangeResult(is_valid=False)

        return DirectionChangeResult(
            is_valid=True,
            cosine=val_cosine,
            polygon=val_polygon
        )
