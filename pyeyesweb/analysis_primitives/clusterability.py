import numpy as np
from typing import  Dict
from sklearn.neighbors import NearestNeighbors

from pyeyesweb.data_models.sliding_window import SlidingWindow


class Clusterability:
    """
    Compute clusterability metric.

    Clusterability measures how strongly a dataset tends to form clusters rather than being randomly distributed.

    Parameters
    ----------
    n_neighbors : int
        Number of nearest neighbors used in the Hopkins statistic computation.

    Notes
    -----

    The Hopkins statistic is a commonly used measure of clusterability.
    It compares the distances of points in the dataset to their nearest neighbors with distances
    from uniformly distributed random points to their nearest neighbors in the dataset.

    If points are aggregated, Clusterability approached 1, whereas a value close to 0.5 suggests randomness.

    Read more in the [User Guide](/PyEyesWeb/user_guide/theoretical_framework/analysis_primitives/clusterability/)

    References
    ----------
    Lawson, R. G., & Jurs, P. C. (1990). New index for clustering tendency and its application to chemical problems.
    Journal of chemical information and computer sciences, 30(1), 36-41.
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

    def _compute_hopkins_statistic(self, data: np.ndarray) -> float:
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

        # Uniform random sample
        uniform_sample = np.random.uniform(mins, maxs, size=data.shape)

        # Compute nearest neighbor distances
        n_neighbors = min(data.shape[0], self.n_neighbors)
        neighbors = NearestNeighbors(n_neighbors=n_neighbors).fit(data)

        # Distances from data points to their nearest neighbors
        data_distances, _ = neighbors.kneighbors(data)
        u = np.sum(data_distances[:, 1])  # exclude self-distance (0)

        # Distances from uniform sample points to their nearest neighbors
        uniform_distances, _ = neighbors.kneighbors(uniform_sample)
        w = np.sum(uniform_distances[:, 0])

        hopkins_stat = w / (u + w + 1e-10)
        return float(hopkins_stat)

    def _compute_clusterability(self, signals: SlidingWindow) -> Dict[str, float]:
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
            - 'clusterability' (float): Computed clusterability value.
              Returns NaN if the window is not full or computation fails.
        """
        if not signals.is_full():
            return {"clusterability": np.nan}

        try:
            data, _ = signals.to_array()
            hopkins_value = self._compute_hopkins_statistic(data)
        except Exception:
            # TODO: add logging for better traceability
            hopkins_value = np.nan

        return {"clusterability": hopkins_value}

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
            Output of `_compute_clusterability`.
        """
        return self._compute_clusterability(sliding_window)
