from dataclasses import dataclass
import numpy as np
from sklearn.neighbors import NearestNeighbors

from pyeyesweb.low_level.base import DynamicFeature
from pyeyesweb.data_models.results import FeatureResult


@dataclass(slots=True)
class ClusterabilityResult(FeatureResult):
    """Output contract for Clusterability."""
    clusterability: float = 0.0


class Clusterability(DynamicFeature):
    """Compute clusterability metric (Hopkins statistic)."""

    def __init__(self, n_neighbors: int) -> None:
        super().__init__()
        self.n_neighbors = n_neighbors

    def _compute_window(self, window_data: np.ndarray) -> ClusterabilityResult:
        # Flatten (Time, Signals, Dims) -> (Time, Features)
        data = window_data.reshape(window_data.shape[0], -1)

        if data.shape[0] < 5:
            return ClusterabilityResult(is_valid=False)

        # Generate uniform random sample within data bounds
        mins = np.min(data, axis=0)
        maxs = np.max(data, axis=0)
        uniform_sample = np.random.uniform(mins, maxs, size=data.shape)

        n_neighbors = min(data.shape[0], self.n_neighbors)
        neighbors = NearestNeighbors(n_neighbors=n_neighbors).fit(data)

        # Data vs Uniform distances
        data_distances, _ = neighbors.kneighbors(data)
        u = np.sum(data_distances[:, 1])  # exclude self-distance (0)

        uniform_distances, _ = neighbors.kneighbors(uniform_sample)
        w = np.sum(uniform_distances[:, 0])

        hopkins_stat = w / (u + w + 1e-10)

        return ClusterabilityResult(clusterability=float(hopkins_stat))
