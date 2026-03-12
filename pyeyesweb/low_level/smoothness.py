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
        # Standard parameter validation
        self.rate_hz = validate_numeric(rate_hz, 'rate_hz', min_val=0.01, max_val=100000)
        self.use_filter = validate_boolean(use_filter, 'use_filter')

        # SPARC parameters initialization
        self.sparc_threshold = validate_numeric(sparc_amplitude_threshold, 'sparc_threshold', min_val=0.0, max_val=1.0)
        self.sparc_min_fc = validate_numeric(sparc_min_fc, 'sparc_min_fc', min_val=0.1)
        self.sparc_max_fc = validate_numeric(sparc_max_fc, 'sparc_max_fc', min_val=self.sparc_min_fc)

        target_metrics = metrics if metrics is not None else self._ALLOWED_METRICS
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

        if "sparc" in self._metrics:
            # Pass custom parameters to the function in math_utils
            sparc_val = float(compute_sparc(
                filtered_speed, 
                rate_hz=self.rate_hz,
                amplitude_threshold=self.sparc_threshold,
                min_fc=self.sparc_min_fc,
                max_fc=self.sparc_max_fc
            ))

        if "jerk_rms" in self._metrics:
            # Standard Jerk RMS calculation from velocity
            jerk_val = float(compute_jerk_rms(filtered_speed, self.rate_hz, signal_type='velocity'))

        return SmoothnessResult(sparc=sparc_val, jerk_rms=jerk_val)