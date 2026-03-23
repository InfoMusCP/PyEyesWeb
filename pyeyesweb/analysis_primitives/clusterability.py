"""Clusterability analysis based on the Hopkins Statistic.

This module implements the [Clusterability][pyeyesweb.analysis_primitives.clusterability.Clusterability]
feature, which evaluates whether a set of points in a given window exhibits
a non-random, clustered structure.
"""

from dataclasses import dataclass
import numpy as np
from sklearn.neighbors import NearestNeighbors

from pyeyesweb.data_models.base import DynamicFeature
from pyeyesweb.data_models.results import FeatureResult


@dataclass(slots=True)
class ClusterabilityResult(FeatureResult):
    """Output contract for Clusterability.
    
    Attributes
    ----------
    clusterability : float
        The Hopkins Statistic value in `[0, 1]`. Values close to `1.0`
        indicate highly clustered data; values near `0.5` indicate random
        uniform distribution.
    """
    clusterability: float = 0.0


class Clusterability(DynamicFeature):
    r"""Compute the clusterability of motion data using the Hopkins statistic.

    Notes
    -----
    The $H$ statistic is calculated as:

    $$ H = \frac{W}{U + W} $$

    where $U$ is the sum of distances from data points to their nearest
    neighbors and $W$ is the sum of distances from random points (drawn
    from a uniform distribution over the data range) to their nearest
    neighbors in the data.

    !!! note
        The Hopkins statistic evaluates the clustering tendency of a dataset by
        comparing the distances between points in the dataset to the distances
        between points in a synthetic uniform distribution.

    Read more in the [User Guide](../../user_guide/theoretical_framework/analysis_primitives/clusterability.md).

    Parameters
    ----------
    n_neighbors : int
        The number of neighbors to consider for the nearest neighbor
        calculations.

    Examples
    --------
    >>> clus = Clusterability(n_neighbors=2)
    """

    def __init__(self, n_neighbors: int) -> None:
        super().__init__()
        self.n_neighbors = n_neighbors

    @property
    def n_neighbors(self) -> int:
        """The number of neighbors for the nearest neighbor search."""
        return self._n_neighbors

    @n_neighbors.setter
    def n_neighbors(self, value: int):
        self._n_neighbors = int(value)

    def compute(self, window_data: np.ndarray) -> ClusterabilityResult:
        r"""Compute the Hopkins statistic for the given time window.

        Parameters
        ----------
        window_data : numpy.ndarray
            Feature window to analyze of shape `(Time, N_signals, N_dims)`.

        Returns
        -------
        ClusterabilityResult
            Result containing the statistic $H$. Returns
            `ClusterabilityResult(is_valid=False)` when fewer than 5 samples
            are available.
        """
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
