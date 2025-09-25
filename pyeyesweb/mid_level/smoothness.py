import numpy as np

from pyeyesweb.data_models.sliding_window import SlidingWindow
from pyeyesweb.utils.signal_processing import apply_savgol_filter
from pyeyesweb.utils.math_utils import compute_sparc, compute_jerk_rms, normalize_signal


class Smoothness:
    def __init__(self, rate_hz=50.0, use_filter=True):
        self.rate_hz = rate_hz
        self.use_filter = use_filter

    def _filter_signal(self, signal):
        """Apply Savitzky-Golay filter if enabled and enough data."""
        if not self.use_filter:
            return np.array(signal)
        return apply_savgol_filter(signal, self.rate_hz)

    def __call__(self, sliding_window: SlidingWindow):
        if len(sliding_window) < 5:
            return None, None

        signal, _ = sliding_window.to_array()

        filtered = self._filter_signal(signal.squeeze())
        normalized = normalize_signal(filtered)

        sparc = compute_sparc(normalized, self.rate_hz)
        jerk = compute_jerk_rms(filtered, self.rate_hz)

        print(f"SPARC: {sparc:.3f}, Jerk RMS: {jerk:.3f}")
        return sparc, jerk
