"""Statistical moments analysis for motion signals.

This module implements the [StatisticalMoment][pyeyesweb.analysis_primitives.statistical_moment.StatisticalMoment]
feature, which computes basic statistical descriptive measures (mean,
variance, skewness, kurtosis) over a sliding window.
"""

from dataclasses import dataclass
from typing import Literal, List, Dict, Optional
import numpy as np
from scipy import stats

from pyeyesweb.data_models.base import DynamicFeature
from pyeyesweb.data_models.results import FeatureResult
from pyeyesweb.utils.validators import validate_string


@dataclass(slots=True)
class StatisticalMomentResult(FeatureResult):
    """Output contract for Statistical Moments.
    
    Contains the computed moments for each signal dimension in the window.
    
    Attributes
    ----------
    mean : list of float, optional
        Arithmetic mean of each feature.
    std_dev : list of float, optional
        Sample standard deviation of each feature.
    skewness : list of float, optional
        Fisher-Pearson coefficient of skewness.
    kurtosis : list of float, optional
        Fisher's definition of kurtosis (excess kurtosis).
    """
    mean: Optional[List[float]] = None
    std_dev: Optional[List[float]] = None
    skewness: Optional[List[float]] = None
    kurtosis: Optional[List[float]] = None

    def to_flat_dict(self, prefix: str = "") -> Dict[str, float]:
        """Dynamically unroll list metrics into scalar dictionary entries.

        Parameters
        ----------
        prefix : str, optional
            Prefix for the dictionary keys.

        Returns
        -------
        Dict[str, float]
            Flattened dictionary where lists are expanded to `metric_index`.
        """
        # FeatureResult.to_flat_dict bypasses the super() slots bug!
        flat = FeatureResult.to_flat_dict(self, prefix)

        def make_key(base: str, idx: int) -> str:
            return f"{prefix}_{base}_{idx}" if prefix else f"{base}_{idx}"

        # Unroll list properties dynamically
        for metric in ["mean", "std_dev", "skewness", "kurtosis"]:
            key = f"{prefix}_{metric}" if prefix else metric
            vals = flat.pop(key, None)
            if vals is not None:
                for i, val in enumerate(vals):
                    flat[make_key(metric, i)] = float(val)

        return flat


class StatisticalMoment(DynamicFeature):
    """Real-time statistical moments analyzer for signal data.

    Computes requested moments independently for each dimension of the input
    window.

    Read more in the [User Guide](../../user_guide/theoretical_framework/analysis_primitives/statistical_moment.md).

    Parameters
    ----------
    metrics : list of str, optional
        List of moments to compute. Choices: `"mean"`, `"std_dev"`,
        `"skewness"`, `"kurtosis"`. Defaults to `["mean"]`.

    Examples
    --------
    >>> mom = StatisticalMoment(metrics=["mean", "std_dev"])
    """

    _ALLOWED_METRICS = ["mean", "std_dev", "skewness", "kurtosis"]
    _MIN_SAMPLES = {"mean": 1, "std_dev": 2, "skewness": 3, "kurtosis": 4}

    def __init__(self, metrics: List[Literal["mean", "std_dev", "skewness", "kurtosis"]] = None):
        super().__init__()
        self.metrics = metrics

    @property
    def metrics(self) -> List[str]:
        """List of active statistical metrics."""
        return self._metrics

    @metrics.setter
    def metrics(self, value: Optional[List[str]]):
        target_metrics = value or ["mean"]
        self._metrics = [validate_string(m, self._ALLOWED_METRICS) for m in target_metrics]

    def compute(self, window_data: np.ndarray, **kwargs) -> StatisticalMomentResult:
        """Compute requested statistical moments for the window.

        Parameters
        ----------
        window_data : numpy.ndarray of shape (Time, N_signals, N_dims)
            Input motion data.
        **kwargs
            Unused; accepted for API compatibility.

        Returns
        -------
        StatisticalMomentResult
            Result containing the requested moments.  Returns
            `StatisticalMomentResult(is_valid=False)` if no metrics could be
            computed due to insufficient samples.
        """
        # Reshape to (Time, Features)
        data = window_data.reshape(window_data.shape[0], -1)
        n_samples = data.shape[0]

        results = {}
        for metric in self._metrics:
            if n_samples >= self._MIN_SAMPLES[metric]:
                if metric == "mean":
                    results["mean"] = np.mean(data, axis=0).tolist()
                elif metric == "std_dev":
                    # ddof=1 for sample standard deviation
                    results["std_dev"] = np.std(data, axis=0, ddof=1).tolist()
                elif metric == "skewness":
                    results["skewness"] = stats.skew(data, axis=0).tolist()
                elif metric == "kurtosis":
                    results["kurtosis"] = stats.kurtosis(data, axis=0).tolist()

        if not results:
            return StatisticalMomentResult(is_valid=False)

        return StatisticalMomentResult(is_valid=True, **results)