"""Movement smoothness analysis module.

This module provides tools for quantifying the smoothness of movement signals
using multiple metrics including SPARC (Spectral Arc Length) and Jerk RMS.
Designed for real time analysis of motion capture or sensor data.

Smoothness metrics are important indicators of movement quality in:
1. Motor control assessment
2. Rehabilitation monitoring
3. Skill learning evaluation
4. Neurological disorder diagnosis
"""

import numpy as np

from pyeyesweb.data_models.sliding_window import SlidingWindow
from pyeyesweb.utils.signal_processing import apply_savgol_filter
from pyeyesweb.utils.math_utils import compute_sparc, compute_jerk_rms, normalize_signal


class Smoothness:
    """Compute movement smoothness metrics from signal data.

    This class analyzes movement smoothness using SPARC (Spectral Arc Length)
    and Jerk RMS metrics. It can optionally apply Savitzky-Golay filtering
    to reduce noise before analysis.

    Parameters
    ----------
    rate_hz : float, optional
        Sampling rate of the signal in Hz (default: 50.0).
    use_filter : bool, optional
        Whether to apply Savitzky-Golay filtering before analysis (default: True).

    Attributes
    ----------
    rate_hz : float
        Signal sampling rate.
    use_filter : bool
        Filter application flag.

    Examples
    --------
    >>> from pyeyesweb.mid_level.smoothness import Smoothness
    >>> from pyeyesweb.data_models.sliding_window import SlidingWindow
    >>>
    >>> smooth = Smoothness(rate_hz=100.0, use_filter=True)
    >>> window = SlidingWindow(max_length=200, n_columns=1)
    >>>
    >>> # Add movement data
    >>> for value in movement_data:
    ...     window.append([value])
    >>>
    >>> sparc, jerk = smooth(window)
    >>> print(f"SPARC: {sparc:.3f}, Jerk RMS: {jerk:.3f}")

    Notes
    -----
    1. SPARC: More negative values indicate smoother movement
    2. Jerk RMS: Lower values indicate smoother movement
    3. Requires at least 5 samples for meaningful analysis
    """

    def __init__(self, rate_hz=50.0, use_filter=True):
        self.rate_hz = rate_hz
        self.use_filter = use_filter

    def _filter_signal(self, signal):
        """Apply Savitzky-Golay filter if enabled and enough data.

        Parameters
        ----------
        signal : array-like
            Input signal to filter.

        Returns
        -------
        ndarray
            Filtered signal or original if filtering disabled/not possible.
        """
        if not self.use_filter:
            return np.array(signal)
        return apply_savgol_filter(signal, self.rate_hz)

    def __call__(self, sliding_window: SlidingWindow):
        """Compute smoothness metrics from windowed signal data.

        Parameters
        ----------
        sliding_window : SlidingWindow
            Buffer containing signal data to analyze.

        Returns
        -------
        sparc : float or None
            Spectral Arc Length (more negative = smoother).
            Returns None if insufficient data.
        jerk : float or None
            RMS of jerk (third derivative).
            Returns None if insufficient data.

        Output
        ------------
        Prints smoothness metrics to stdout.
        """
        if len(sliding_window) < 5:
            return None, None

        signal, _ = sliding_window.to_array()

        filtered = self._filter_signal(signal.squeeze())
        normalized = normalize_signal(filtered)

        sparc = compute_sparc(normalized, self.rate_hz)
        jerk = compute_jerk_rms(filtered, self.rate_hz)

        print(f"SPARC: {sparc:.3f}, Jerk RMS: {jerk:.3f}")
        return sparc, jerk