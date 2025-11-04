import numpy as np
from typing import  Dict
from sklearn.neighbors import NearestNeighbors

from pyeyesweb.data_models.sliding_window import SlidingWindow


class Clusterability:
    """
    Compute clusterability metrics (Hopkins statistic) for streaming or batched data.

    Parameters
    ----------
    n_neighbors : int
        Number of nearest neighbors used in the Hopkins statistic computation.

    Notes
    -----

    References
    ----------

    """

    def __init__(self, n_neighbors: int) -> None:
        """
        Initialize the Clusterability object.

        Parameters
        ----------
        n_neighbors : int
            Number of nearest neighbors to use in the Hopkins statistic computation.
        random_state : int, optional
            Random seed for reproducibility. Default is None.
        """
        self.n_neighbors = n_neighbors

    def compute_hopkins_statistic(self, data: np.ndarray) -> float:
        """
        Compute the Hopkins statistic for a given dataset.

        Parameters
        ----------
        data : np.ndarray
            Input data of shape (n_samples, n_features).

        Returns
        -------
        float
            Hopkins statistic value. Returns NaN if data is insufficient or invalid.
        """
        if data.shape[0] < 5:
            return np.nan

        # Generate uniform random sample within data bounds
        mins = np.min(data, axis=0)
        maxs = np.max(data, axis=0)
        data_norm = (data - mins) / (maxs - mins + 1e-10)

        # Uniform random sample
        uniform_sample = np.random.uniform(mins, maxs, size=data.shape)

        # Compute nearest neighbor distances
        n_neighbors = min(data.shape[0], self.n_neighbors)
        neighbors = NearestNeighbors(n_neighbors=n_neighbors).fit(data_norm)

        # Distances from data points to their nearest neighbors
        data_distances, _ = neighbors.kneighbors(data_norm)
        u = np.sum(data_distances[:, 1])  # exclude self-distance (0)

        # Distances from uniform sample points to their nearest neighbors
        uniform_distances, _ = neighbors.kneighbors(uniform_sample)
        w = np.sum(uniform_distances[:, 0])

        hopkins_stat = u / (u + w + 1e-10)
        return float(hopkins_stat)

    def compute_clusterability(self, signals: SlidingWindow) -> Dict[str, float]:
        """
        Compute the clusterability of a sliding window of signals using the Hopkins statistic.

        Parameters
        ----------
        signals : SlidingWindow
            A sliding window object containing signal data.

        Returns
        -------
        dict
            Dictionary containing:
            - 'hopkins_statistic' (float): Computed Hopkins statistic.
              Returns NaN if the window is not full or computation fails.
        """
        if not signals.is_full():
            return {"hopkins_statistic": np.nan}

        try:
            data, _ = signals.to_array()
            hopkins_value = self.compute_hopkins_statistic(data)
        except Exception:
            # TODO: add logging for better traceability
            hopkins_value = np.nan

        return {"hopkins_statistic": hopkins_value}

    def __call__(self, sliding_window: SlidingWindow) -> Dict[str, float]:
        """
        Callable interface to compute clusterability directly on a SlidingWindow instance.

        Parameters
        ----------
        sliding_window : SlidingWindow
            The sliding window object containing the data.

        Returns
        -------
        dict
            Output of `compute_clusterability`.
        """
        return self.compute_clusterability(sliding_window)
