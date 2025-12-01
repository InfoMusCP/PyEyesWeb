"""Statistical moments analysis module for signal processing.

This module provides tools for computing various statistical moments from
multivariate signal data. Statistical moments characterize the shape and
properties of probability distributions and are fundamental in signal analysis.

The available statistical moments include:
1. Mean - Central tendency of the data
2. Standard Deviation - Dispersion around the mean
3. Skewness - Asymmetry of the distribution
4. Kurtosis - Tailedness of the distribution

Typical use cases include:
1. Signal characterization and feature extraction
2. Quality assessment of sensor data
3. Motion pattern analysis in movement data
4. Anomaly detection in time series data
5. Distribution analysis in multivariate signals

References
----------
1. Pearson, K. (1895). Contributions to the Mathematical Theory of Evolution.
2. Fisher, R. A. (1925). Statistical Methods for Research Workers.
"""

import numpy as np
from scipy import stats
from pyeyesweb.data_models.sliding_window import SlidingWindow


class StatisticalMoment:
    """Real time statistical moments analyzer for signal data.

    This class computes various statistical moments (mean, standard deviation,
    skewness, kurtosis) from sliding window data to characterize signal
    distributions and properties.
    """

    def __init__(self):
        # No parameters in constructor as per comments
        pass

    def compute_statistics(self, signals: SlidingWindow, methods: list) -> dict:
        """Compute statistical analysis for multivariate signals.

        Parameters
        ----------
        signals : SlidingWindow
            Sliding window buffer containing multivariate signal data.
        methods : list of str
            List of statistical methods to compute. Available options:
            'mean', 'std_dev', 'skewness', 'kurtosis'

        Returns
        -------
        dict
            Dictionary containing statistical metrics.
        """
        if not signals.is_full():
            return np.nan

        data, _ = signals.to_array()
        n_samples, n_features = data.shape

        if n_samples < 2:
            return np.nan

        result = {}

        # Compute only the requested statistical moments
        for method in methods:
            if method == 'mean':
                values = np.mean(data, axis=0)
                result['mean'] = float(values[0]) if len(values) == 1 else values.tolist()

            elif method == 'std_dev':
                values = np.std(data, axis=0, ddof=1)
                result['std'] = float(values[0]) if len(values) == 1 else values.tolist()

            elif method == 'skewness':
                values = stats.skew(data, axis=0)
                result['skewness'] = float(values[0]) if len(values) == 1 else values.tolist()

            elif method == 'kurtosis':
                values = stats.kurtosis(data, axis=0)
                result['kurtosis'] = float(values[0]) if len(values) == 1 else values.tolist()

            else:
                # Skip invalid methods silently
                continue

        return result

    def __call__(self, sliding_window: SlidingWindow, methods: list) -> dict:
        """Compute statistical metrics.

        Parameters
        ----------
        sliding_window : SlidingWindow
            Buffer containing multivariate data to analyze.
        methods : list of str
            List of statistical methods to compute.

        Returns
        -------
        dict
            Dictionary containing statistical metrics.
        """
        return self.compute_statistics(sliding_window, methods)