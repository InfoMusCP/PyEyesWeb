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

from typing import Literal
import numpy as np
from scipy import stats
from pyeyesweb.data_models.sliding_window import SlidingWindow
from pyeyesweb.utils.validators import validate_string


class StatisticalMoment:
    """Real time statistical moments analyzer for signal data.

    This class computes various statistical moments (mean, standard deviation,
    skewness, kurtosis) from sliding window data to characterize signal
    distributions and properties.
    """
    _ALLOWED_METHODS = ["mean", "std_dev", "skewness", "kurtosis"]
    _MIN_SAMPLES = {"mean": 1, "std_dev": 2, "skewness": 3, "kurtosis": 4}

    def __init__(
        self,
        methods: list[Literal["mean", "std_dev", "skewness", "kurtosis"]] = ["mean"],
    ):
        """Initialize the statistical moment analyzer.

        Parameters
        ----------
        methods : list of str
            List of statistical methods to compute. Available options:
            'mean', 'std_dev', 'skewness', 'kurtosis'
        """
        self._methods = [validate_string(method, self._ALLOWED_METHODS) for method in methods]

    def _compute_statistics(self, data: np.ndarray, methods: list[str]) -> dict:
        """Compute statistical analysis for multivariate signals.

        Parameters
        ----------
        data : np.ndarray
            Input signal data array.

        Returns
        -------
        dict
            Dictionary containing statistical metrics.
        """
        result = {}

        for method in methods:
            if method == "mean":
                result["mean"] = np.mean(data, axis=0)

            elif method == "std_dev":
                result["std"] = np.std(data, axis=0, ddof=1)

            elif method == "skewness":
                result["skewness"] = stats.skew(data, axis=0)

            elif method == "kurtosis":
                result["kurtosis"] = stats.kurtosis(data, axis=0)

        return result

    def __call__(self, signal: SlidingWindow) -> dict:
        """Compute statistical metrics.

        Parameters
        ----------
        signal : SlidingWindow
            Buffer containing multivariate data to analyze.

        Returns
        -------
        dict
            Dictionary containing statistical metrics.
        """
        if signal.get_num_signals() != 1:
            raise ValueError("Number of signals must be exactly one.")
        data, _ = signal.to_array(as2D=True)
        n_samples, n_features = data.shape
        methods = self._methods
        
        results = {}
        if n_samples < max(self._MIN_SAMPLES[method] for method in methods):
            for method in reversed(methods):
                if n_samples < self._MIN_SAMPLES[method]:
                    results[method] = np.nan
                    methods.remove(method)

        results.update(self._compute_statistics(data, methods))
        return results