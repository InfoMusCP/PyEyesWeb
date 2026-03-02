from dataclasses import dataclass
import numpy as np

from pyeyesweb.low_level.base import DynamicFeature
from pyeyesweb.data_models.results import FeatureResult
from pyeyesweb.utils.validators import validate_numeric, validate_and_normalize_filter_params
from pyeyesweb.utils.signal_processing import compute_phase_synchronization


@dataclass(slots=True)
class SynchronizationResult(FeatureResult):
    """Output contract for Phase Synchronization."""
    plv: float = 0.0


class Synchronization(DynamicFeature):
    """Real time phase synchronization analyzer for paired signals."""

    def __init__(self, filter_params=None, phase_threshold=0.7):
        super().__init__()
        self.phase_threshold = validate_numeric(phase_threshold, 'phase_threshold', min_val=0, max_val=1)
        self.filter_params = validate_and_normalize_filter_params(filter_params)

    def _compute_window(self, window_data: np.ndarray) -> SynchronizationResult:
        # Flatten to (Time, Signals)
        data = window_data.reshape(window_data.shape[0], -1)

        if data.shape[1] < 2:
            return SynchronizationResult(is_valid=False)

        try:
            # Assumes compute_phase_synchronization expects a 2D array of (Time, N_Signals)
            plv = compute_phase_synchronization(data, self.filter_params)
            return SynchronizationResult(plv=float(plv))
        except Exception:
            return SynchronizationResult(is_valid=False)