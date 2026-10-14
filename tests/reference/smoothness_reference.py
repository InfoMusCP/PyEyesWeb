from typing import Literal, List, Optional
import numpy as np
from scipy.signal import butter, filtfilt

from pyeyesweb.catalog import Layer, describe
from legacy_base import DynamicFeature
from pyeyesweb.data_models.results import Output, Schema, Status
from legacy_utils import (
    compute_sparc, 
    compute_jerk_rms, 
    compute_ldlj,
    compute_sample_entropy,
    compute_harmonicity_index,
    compute_submovement_count
)
from pyeyesweb.utils.validators import validate_numeric, validate_boolean, validate_string


@describe(Layer.LOW_LEVEL)
class SpeedSmoothnessReference(DynamicFeature):
    """Calculates movement smoothness and complexity metrics from a 1D speed profile.

    Returns
    -------
    Result
        One scalar output per requested metric among `sparc`, `jerk_rms`, `ldlj_v`, `ldlj_a`, `samp_en`,
        `harmonicity` (float) and `n_submovements` (int); `feature.outputs` lists exactly the requested ones.
        `Status.WARMING_UP` when the window holds fewer than 10 samples.
    """

    _OUTPUTS = Schema(
        Output("sparc", doc="Spectral arc length (SPARC); closer to 0 is smoother."),
        Output("jerk_rms", doc="Root-mean-square jerk of the speed profile."),
        Output("ldlj_v", doc="Log dimensionless jerk computed on the velocity signal."),
        Output("ldlj_a", doc="Log dimensionless jerk computed on the acceleration signal."),
        Output("samp_en", doc="Sample entropy of the speed profile."),
        Output("harmonicity", doc="Harmonicity index of the speed profile."),
        Output("n_submovements", kind=int, doc="Number of detected submovements."),
    )

    def _schema(self) -> Schema:
        return self._OUTPUTS.select(self.metrics)

    _ALLOWED_METRICS = [
        "sparc", "jerk_rms", "ldlj_v", "ldlj_a", 
        "samp_en", "harmonicity", "n_submovements"
    ]

    def __init__(
            self,
            rate_hz: float = 50.0,
            use_filter: bool = True,
            metrics: List[Literal["sparc", "jerk_rms", "ldlj_v", "ldlj_a", "samp_en", "harmonicity", "n_submovements"]] = None,
            sparc_amplitude_threshold: float = 0.05,
            sparc_min_fc: float = 2.0,
            sparc_max_fc: float = 20.0,
            min_speed_threshold: float = 30.0
    ):
        super().__init__()
        self.rate_hz = rate_hz
        self.use_filter = use_filter
        
        self.sparc_min_fc = sparc_min_fc
        self.sparc_max_fc = sparc_max_fc
        self.sparc_threshold = sparc_amplitude_threshold
        self.min_speed_threshold = min_speed_threshold

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
        min_fc = getattr(self, '_sparc_min_fc', 0.1)
        self._sparc_max_fc = validate_numeric(value, 'sparc_max_fc', min_val=min_fc)

    @property
    def metrics(self) -> List[str]:
        return self._metrics

    @metrics.setter
    def metrics(self, value: Optional[List[str]]):
        target_metrics = value if value is not None else self._ALLOWED_METRICS
        self._metrics = [validate_string(metric_name, self._ALLOWED_METRICS) for metric_name in target_metrics]
        self._outputs_changed()

    def _filter_signal(self, signal: np.ndarray) -> np.ndarray:
        if not self.use_filter:
            return signal

        cutoff = min(10.0, (self.rate_hz / 2.0) - 1.0)
        numerator, denominator = butter(4, cutoff / (self.rate_hz / 2.0), btype='low')

        # filtfilt requires the signal to be strictly longer than its default padlen
        if len(signal) <= 3 * max(len(denominator), len(numerator)):
            return signal
        return filtfilt(numerator, denominator, signal)

    def compute(self, window_data: np.ndarray):
        if window_data.size != window_data.shape[0]:
            raise ValueError("Smoothness expects a 1D speed profile.")

        speed_profile = window_data.ravel()
        
        if len(speed_profile) < 10:
            return self._no_output(Status.WARMING_UP, "fewer than 10 samples")

        # Zero-velocity check
        # if np.mean(speed_profile) < self.min_speed_threshold or np.max(speed_profile) < (self.min_speed_threshold * 1.5):
        #    return self._no_output(Status.INVALID_INPUT, "speed below threshold")

        filtered_speed = self._filter_signal(speed_profile)

        values = {}

        if "sparc" in self.metrics:
            values["sparc"] = float(compute_sparc(
                filtered_speed,
                rate_hz=self.rate_hz,
                amplitude_threshold=self.sparc_threshold,
                min_fc=self.sparc_min_fc,
                max_fc=self.sparc_max_fc
            ))

        if "jerk_rms" in self.metrics:
            values["jerk_rms"] = float(compute_jerk_rms(filtered_speed, self.rate_hz, signal_type='velocity'))

        if "ldlj_v" in self.metrics:
            values["ldlj_v"] = float(compute_ldlj(filtered_speed, self.rate_hz, signal_type='velocity'))

        if "ldlj_a" in self.metrics:
            values["ldlj_a"] = float(compute_ldlj(filtered_speed, self.rate_hz, signal_type='acceleration'))

        if "samp_en" in self.metrics:
            values["samp_en"] = float(compute_sample_entropy(filtered_speed))

        if "harmonicity" in self.metrics:
            values["harmonicity"] = float(compute_harmonicity_index(filtered_speed, self.rate_hz))

        if "n_submovements" in self.metrics:
            values["n_submovements"] = int(compute_submovement_count(filtered_speed, self.rate_hz))

        return self._result(**values)


__all__ = ["SpeedSmoothnessReference"]
