"""Clusterability analysis module for Hopkins statistic computation.

This module provides tools for computing the Hopkins statistic to assess
the clusterability of multivariate data. The Hopkins statistic measures
the spatial randomness of data points and indicates whether meaningful
clustering structure exists.

The Hopkins statistic computation follows these steps:
1. Sample points from the actual data distribution
2. Generate uniform random points within the data space
3. Compute distances to nearest neighbors for both sample types
4. Calculate the Hopkins statistic from distance ratios

The Hopkins statistic ranges from 0 to 1:
- Values close to 0.5 indicate random data distribution
- Values significantly above 0.5 indicate clusterable data
- Values significantly below 0.5 indicate uniformly distributed data

Typical use cases include:
1. Pre-clustering analysis to determine if clustering is appropriate
2. Quality assessment of feature spaces in machine learning
3. Motion pattern analysis in movement data
4. Spatial distribution analysis in sensor data

References
----------
1. Hopkins, B. & Skellam, J. G. (1954). A new method for determining
   the type of distribution of plant individuals. Annals of Botany.
2. Lawson, R. G. & Jurs, P. C. (1990). New index for clustering tendency
   detection. Journal of Chemical Information and Computer Sciences.
"""

import numpy as np
from sklearn.neighbors import NearestNeighbors

from pyeyesweb.data_models.sliding_window import SlidingWindow


class Clusterability:
    """Real time clusterability analyzer using Hopkins statistic.

    This class computes the Hopkins statistic to assess whether data exhibits
    meaningful clustering structure.

    Parameters
    ----------
    n_neighbors : int
        Number of neighbors to use for nearest neighbor computation.
    random_state : int or None, optional
        Random seed for reproducible sampling. If None, uses random sampling
        (default: None).
    """

    def __init__(self, n_neighbors, random_state=None):
        self.n_neighbors = n_neighbors

        if random_state is not None:
            if not isinstance(random_state, int):
                raise TypeError("random_state must be integer or None")
            if random_state < 0:
                raise ValueError("random_state must be non-negative")
        self.random_state = random_state

    def compute_hopkins_statistic(self, data: np.ndarray) -> float:
        """Compute Hopkins statistic for clusterability assessment.

        Parameters
        ----------
        data : np.ndarray
            Multivariate data array of shape (n_samples, n_features).

        Returns
        -------
        float
            Hopkins statistic value between 0 and 1, or np.nan if computation fails.
        """
        if data.ndim != 2:
            raise ValueError(f"Data must be 2D array, got {data.ndim}D")

        n_samples, n_features = data.shape

        if n_samples < 2:
            return np.nan

        if n_features < 1:
            return np.nan

        # Use fixed sample fraction of 0.1 as default
        sample_fraction = 0.1
        sample_size = max(1, int(sample_fraction * n_samples))
        sample_size = min(sample_size, n_samples - 1)  # Leave at least one sample for neighbors

        if self.random_state is not None:
            np.random.seed(self.random_state)

        # Sample from actual data
        data_indices = np.random.choice(n_samples, size=sample_size, replace=False)
        data_sample = data[data_indices]

        # Generate uniform random sample within data bounds
        mins = np.min(data, axis=0)
        maxs = np.max(data, axis=0)
        ranges = maxs - mins

        if np.any(ranges <= 0):
            return np.nan

        uniform_sample = np.random.uniform(mins, maxs, size=(sample_size, n_features))

        # Compute nearest neighbor distances
        try:
            nbrs = NearestNeighbors(n_neighbors=min(self.n_neighbors + 1, n_samples), algorithm='auto').fit(data)

            # Distances from data sample points to their nearest neighbors in original data
            data_distances, _ = nbrs.kneighbors(data_sample)
            u_distances = data_distances[:, 1]  # Distance to nearest non-self neighbor

            # Distances from uniform sample points to their nearest neighbors in original data
            uniform_distances, _ = nbrs.kneighbors(uniform_sample)
            w_distances = uniform_distances[:, 0]  # Distance to nearest neighbor

            # Compute Hopkins statistic
            numerator = np.sum(w_distances)
            denominator = np.sum(u_distances) + np.sum(w_distances)

            if denominator == 0:
                return np.nan

            hopkins_stat = numerator / denominator
            return float(hopkins_stat)

        except Exception:
            return np.nan

    def compute_clusterability(self, signals: SlidingWindow) -> dict:
        """Compute clusterability analysis for multivariate signals.

        Parameters
        ----------
        signals : SlidingWindow
            Sliding window buffer containing multivariate signal data.

        Returns
        -------
        dict
            Dictionary containing clusterability metrics.
        """
        if not signals.is_full():
            return {
                "hopkins_statistic": np.nan,
                "sample_size": 0,
                "feature_dimension": signals._n_columns
            }

        data, _ = signals.to_array()
        n_samples, n_features = data.shape

        try:
            hopkins_stat = self.compute_hopkins_statistic(data)

            return {
                "hopkins_statistic": hopkins_stat,
                "sample_size": n_samples,
                "feature_dimension": n_features
            }
        except Exception:
            return {
                "hopkins_statistic": np.nan,
                "sample_size": n_samples,
                "feature_dimension": n_features
            }

    def __call__(self, sliding_window: SlidingWindow) -> dict:
        """Compute and optionally display clusterability metrics.

        Parameters
        ----------
        sliding_window : SlidingWindow
            Buffer containing multivariate data to analyze.

        Returns
        -------
        dict
            Dictionary containing clusterability metrics.
        """
        result = self.compute_clusterability(sliding_window)
        hopkins_stat = result["hopkins_statistic"]

        if not np.isnan(hopkins_stat):
            print(f"Hopkins Statistic: {hopkins_stat:.3f}")

        return result