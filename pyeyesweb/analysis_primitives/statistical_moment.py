from dataclasses import dataclass
from typing import Literal, List, Dict, Optional
import numpy as np
from scipy import stats

from pyeyesweb.low_level.base import DynamicFeature
from pyeyesweb.data_models.results import FeatureResult
from pyeyesweb.utils.validators import validate_string


@dataclass(slots=True)
class StatisticalMomentResult(FeatureResult):
    """Output contract for Statistical Moments."""
    mean: Optional[List[float]] = None
    std_dev: Optional[List[float]] = None
    skewness: Optional[List[float]] = None
    kurtosis: Optional[List[float]] = None

    def to_flat_dict(self, prefix: str = "") -> Dict[str, float]:
        """Dynamically unrolls list metrics into scalars (e.g., mean_0, mean_1)."""
        # Note: FeatureResult.to_flat_dict bypasses the super() bug!
        from dataclasses import dataclass
        from typing import Literal, List, Dict, Optional
        import numpy as np
        from scipy import stats

        from pyeyesweb.low_level.base import DynamicFeature
        from pyeyesweb.data_models.results import FeatureResult
        from pyeyesweb.utils.validators import validate_string

        @dataclass(slots=True)
        class StatisticalMomentResult(FeatureResult):
            """Output contract for Statistical Moments."""
            mean: Optional[List[float]] = None
            std_dev: Optional[List[float]] = None
            skewness: Optional[List[float]] = None
            kurtosis: Optional[List[float]] = None

            def to_flat_dict(self, prefix: str = "") -> Dict[str, float]:
                flat = FeatureResult.to_flat_dict(self, prefix)

                def make_key(base: str, idx: int) -> str:
                    return f"{prefix}_{base}_{idx}" if prefix else f"{base}_{idx}"

                for metric in ["mean", "std_dev", "skewness", "kurtosis"]:
                    key = f"{prefix}_{metric}" if prefix else metric
                    vals = flat.pop(key, None)
                    if vals is not None:
                        for i, val in enumerate(vals):
                            flat[make_key(metric, i)] = float(val)

                return flat

        class StatisticalMoment(DynamicFeature):
            """Real time statistical moments analyzer for signal data."""

            _ALLOWED_METRICS = ["mean", "std_dev", "skewness", "kurtosis"]
            _MIN_SAMPLES = {"mean": 1, "std_dev": 2, "skewness": 3, "kurtosis": 4}

            def __init__(self, metrics: List[Literal["mean", "std_dev", "skewness", "kurtosis"]] = None):
                super().__init__()

                # If None, compute everything
                target_metrics = metrics if metrics is not None else self._ALLOWED_METRICS
                self._metrics = [validate_string(m, self._ALLOWED_METRICS) for m in target_metrics]

            def _compute_window(self, window_data: np.ndarray) -> StatisticalMomentResult:
                data = window_data.reshape(window_data.shape[0], -1)
                n_samples = data.shape[0]

                results = {}
                for metric in self._metrics:
                    if n_samples >= self._MIN_SAMPLES[metric]:
                        if metric == "mean":
                            results["mean"] = np.mean(data, axis=0).tolist()
                        elif metric == "std_dev":
                            results["std_dev"] = np.std(data, axis=0, ddof=1).tolist()
                        elif metric == "skewness":
                            results["skewness"] = stats.skew(data, axis=0).tolist()
                        elif metric == "kurtosis":
                            results["kurtosis"] = stats.kurtosis(data, axis=0).tolist()

                if not results:
                    return StatisticalMomentResult(is_valid=False)

                return StatisticalMomentResult(is_valid=True, **results)

        flat = FeatureResult.to_flat_dict(self, prefix)

        def make_key(base: str, idx: int) -> str:
            return f"{prefix}_{base}_{idx}" if prefix else f"{base}_{idx}"

        # Unroll list properties
        for metric in ["mean", "std_dev", "skewness", "kurtosis"]:
            key = f"{prefix}_{metric}" if prefix else metric
            vals = flat.pop(key, None)
            if vals is not None:
                for i, val in enumerate(vals):
                    flat[make_key(metric, i)] = float(val)

        return flat


class StatisticalMoment(DynamicFeature):
    """Real time statistical moments analyzer for signal data."""

    _ALLOWED_METHODS = ["mean", "std_dev", "skewness", "kurtosis"]
    _MIN_SAMPLES = {"mean": 1, "std_dev": 2, "skewness": 3, "kurtosis": 4}

    def __init__(self, methods: List[Literal["mean", "std_dev", "skewness", "kurtosis"]] = None):
        super().__init__()
        methods = methods or ["mean"]
        self._methods = [validate_string(m, self._ALLOWED_METHODS) for m in methods]

    def _compute_window(self, window_data: np.ndarray) -> StatisticalMomentResult:
        # Reshape to (Time, Features)
        data = window_data.reshape(window_data.shape[0], -1)
        n_samples = data.shape[0]
        
        results = {}
        for method in self._methods:
            if n_samples >= self._MIN_SAMPLES[method]:
                if method == "mean":
                    results["mean"] = np.mean(data, axis=0).tolist()
                elif method == "std_dev":
                    results["std_dev"] = np.std(data, axis=0, ddof=1).tolist()
                elif method == "skewness":
                    results["skewness"] = stats.skew(data, axis=0).tolist()
                elif method == "kurtosis":
                    results["kurtosis"] = stats.kurtosis(data, axis=0).tolist()
        
        if not results:
            return StatisticalMomentResult(is_valid=False)

        return StatisticalMomentResult(is_valid=True, **results)