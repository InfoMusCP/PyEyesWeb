from dataclasses import dataclass
from typing import Literal, List, Optional
import numpy as np

from pyeyesweb.low_level.base import DynamicFeature
from pyeyesweb.data_models.results import FeatureResult
from pyeyesweb.utils.signal_processing import apply_savgol_filter
from pyeyesweb.utils.math_utils import compute_sparc, compute_jerk_rms, normalize_signal
from pyeyesweb.utils.validators import validate_numeric, validate_boolean, validate_string


@dataclass(slots=True)
class SmoothnessResult(FeatureResult):
    """Output contract for Smoothness metrics."""
    sparc: Optional[float] = None
    jerk_rms: Optional[float] = None


class Smoothness(DynamicFeature):
    """Compute movement smoothness metrics from an atomic 1D speed profile."""

    _ALLOWED_METRICS = ["sparc", "jerk_rms"]

    def __init__(
            self,
            rate_hz: float = 50.0,
            use_filter: bool = True,
            metrics: List[Literal["sparc", "jerk_rms"]] = None
    ):
        super().__init__()
        self.rate_hz = validate_numeric(rate_hz, 'rate_hz', min_val=0.01, max_val=100000)
        self.use_filter = validate_boolean(use_filter, 'use_filter')

        target_metrics = metrics if metrics is not None else self._ALLOWED_METRICS
        self._metrics = [validate_string(m, self._ALLOWED_METRICS) for m in target_metrics]

    def _filter_signal(self, signal: np.ndarray) -> np.ndarray:
        if not self.use_filter:
            return signal
        return apply_savgol_filter(signal, self.rate_hz)

    def _compute_window(self, window_data: np.ndarray) -> SmoothnessResult:
        if window_data.size != window_data.shape[0]:
            raise ValueError("Smoothness expects a 1D speed profile.")

        speed_profile = window_data.ravel()
        if len(speed_profile) < 5:
            return SmoothnessResult(is_valid=False)

        # 1. Shared Preprocessing
        filtered_speed = self._filter_signal(speed_profile)

        # 2. Selective Execution
        sparc_val = None
        jerk_val = None

        if "sparc" in self._metrics:
            normalized_speed = normalize_signal(filtered_speed)
            sparc_val = float(compute_sparc(normalized_speed, self.rate_hz))

        if "jerk_rms" in self._metrics:
            jerk_val = float(compute_jerk_rms(filtered_speed, self.rate_hz, signal_type='velocity'))

        return SmoothnessResult(sparc=sparc_val, jerk_rms=jerk_val)