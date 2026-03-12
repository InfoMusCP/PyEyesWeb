from dataclasses import dataclass
from typing import Literal, List, Optional
import numpy as np

from pyeyesweb.data_models.base import DynamicFeature
from pyeyesweb.data_models.results import FeatureResult
from pyeyesweb.utils.signal_processing import apply_savgol_filter
from pyeyesweb.utils.math_utils import compute_sparc, compute_jerk_rms
from pyeyesweb.utils.validators import validate_numeric, validate_boolean, validate_string


@dataclass(slots=True)
class SmoothnessResult(FeatureResult):
    """Output contract for Smoothness metrics."""
    sparc: Optional[float] = None
    jerk_rms: Optional[float] = None


class Smoothness(DynamicFeature):
    """
    Calculates movement smoothness metrics from a 1D speed profile.
    """

    _ALLOWED_METRICS = ["sparc", "jerk_rms"]

    def __init__(
            self,
            rate_hz: float = 50.0,
            use_filter: bool = True,
            metrics: List[Literal["sparc", "jerk_rms"]] = None,
            sparc_amplitude_threshold: float = 0.05,
            sparc_min_fc: float = 2.0,
            sparc_max_fc: float = 20.0
    ):
        super().__init__()
        # Initializing through setters natively routes the values to the validators
        self.rate_hz = rate_hz
        self.use_filter = use_filter
        
        self.sparc_min_fc = sparc_min_fc
        self.sparc_max_fc = sparc_max_fc
        self.sparc_threshold = sparc_amplitude_threshold

        self.metrics = metrics

    @property
    def rate_hz(self) -> float:
        return self._rate_hz

    @rate_hz.setter
    def rate_hz(self, value: float):
        self._rate_hz = validate_numeric(value, 'rate_hz', min_val=0.01, max_val=100000)

    @property
    def use_filter(self) -> bool:
        return self._use_filter

    @use_filter.setter
    def use_filter(self, value: bool):
        self._use_filter = validate_boolean(value, 'use_filter')

    @property
    def sparc_threshold(self) -> float:
        return self._sparc_threshold

    @sparc_threshold.setter
    def sparc_threshold(self, value: float):
        self._sparc_threshold = validate_numeric(value, 'sparc_threshold', min_val=0.0, max_val=1.0)

    @property
    def sparc_min_fc(self) -> float:
        return self._sparc_min_fc

    @sparc_min_fc.setter
    def sparc_min_fc(self, value: float):
        self._sparc_min_fc = validate_numeric(value, 'sparc_min_fc', min_val=0.1)

    @property
    def sparc_max_fc(self) -> float:
        return self._sparc_max_fc

    @sparc_max_fc.setter
    def sparc_max_fc(self, value: float):
        # We ensure that this validator uses the dynamic minimum
        min_fc = getattr(self, '_sparc_min_fc', 0.1)
        self._sparc_max_fc = validate_numeric(value, 'sparc_max_fc', min_val=min_fc)

    @property
    def metrics(self) -> List[str]:
        return self._metrics

    @metrics.setter
    def metrics(self, value: Optional[List[str]]):
        target_metrics = value if value is not None else self._ALLOWED_METRICS
        self._metrics = [validate_string(m, self._ALLOWED_METRICS) for m in target_metrics]

    def _filter_signal(self, signal: np.ndarray) -> np.ndarray:
        """Applies Savitzky-Golay filter if enabled."""
        if not self.use_filter:
            return signal
        return apply_savgol_filter(signal, self.rate_hz)

    def compute(self, window_data: np.ndarray) -> SmoothnessResult:
        """Executes smoothness calculation on the speed profile."""
        if window_data.size != window_data.shape[0]:
            raise ValueError("Smoothness expects a 1D speed profile.")

        speed_profile = window_data.ravel()
        
        # Minimum sample threshold for FFT
        if len(speed_profile) < 10:
            return SmoothnessResult(is_valid=False)

        # 1. Preprocessing (Filtering)
        filtered_speed = self._filter_signal(speed_profile)

        # 2. Metrics calculation
        sparc_val = None
        jerk_val = None

        if "sparc" in self.metrics:
            # Pass custom parameters to the function in math_utils
            sparc_val = float(compute_sparc(
                filtered_speed, 
                rate_hz=self.rate_hz,
                amplitude_threshold=self.sparc_threshold,
                min_fc=self.sparc_min_fc,
                max_fc=self.sparc_max_fc
            ))

        if "jerk_rms" in self.metrics:
            # Standard Jerk RMS calculation from velocity
            jerk_val = float(compute_jerk_rms(filtered_speed, self.rate_hz, signal_type='velocity'))

        return SmoothnessResult(sparc=sparc_val, jerk_rms=jerk_val)