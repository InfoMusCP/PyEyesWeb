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
from pyeyesweb.utils.validators import validate_numeric, validate_boolean


class Smoothness:
    """Compute movement smoothness metrics from signal data.

    This class analyzes movement smoothness using SPARC (Spectral Arc Length)
    and Jerk RMS metrics. It can optionally apply Savitzky-Golay filtering
    to reduce noise before analysis.

    SPARC implementation is based on Balasubramanian et al. (2015) "On the analysis
    of movement smoothness" from Journal of NeuroEngineering and Rehabilitation.
    SPARC values are typically negative, with values closer to 0 indicating less
    smooth movements. Healthy reaching movements typically yield SPARC values around
    -1.4 to -1.6, while pathological movements may range from -3 to -10 or lower.

    Read more in the [User Guide](/PyEyesWeb/user_guide/theoretical_framework/low_level/smoothness/)

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
    >>> from pyeyesweb.low_level.smoothness import Smoothness
    >>> from pyeyesweb.data_models.sliding_window import SlidingWindow
    >>> import numpy as np
    >>>
    >>> # Generate sample movement data (simulated velocity profile)
    >>> t = np.linspace(0, 2, 200)
    >>> movement_data = np.sin(2 * np.pi * t) + 0.1 * np.random.randn(200)
    >>>
    >>> smooth = Smoothness(rate_hz=100.0, use_filter=True)
    >>> window = SlidingWindow(max_length=200, n_columns=1)
    >>>
    >>> # Add movement data
    >>> for value in movement_data:
    ...     window.append([value])
    >>>
    >>> result = smooth(window)
    >>> print(f"SPARC: {result['sparc']:.3f}, Jerk RMS: {result['jerk_rms']:.3f}")

    Notes
    -----
    1. SPARC: Values closer to 0 indicate smoother movement (less negative = smoother)
    2. Jerk RMS: Lower values indicate smoother movement
    3. Requires at least 5 samples for meaningful analysis

    References
    ----------
    Balasubramanian, S., Melendez-Calderon, A., Roby-Brami, A., & Burdet, E. (2015).
    On the analysis of movement smoothness. Journal of NeuroEngineering and Rehabilitation,
    12(1), 1-11.
    """

    def __init__(self, rate_hz=50.0, use_filter=True):
        self.rate_hz = validate_numeric(rate_hz, 'rate_hz', min_val=0.01, max_val=100000)
        self.use_filter = validate_boolean(use_filter, 'use_filter')

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
        dict
            Dictionary containing:
            - 'sparc': Spectral Arc Length (closer to 0 = smoother).
                      Returns NaN if insufficient data.
            - 'jerk_rms': RMS of jerk (third derivative).
                         Returns NaN if insufficient data.
        """
        if len(sliding_window) < 5:
            return {"sparc": np.nan, "jerk_rms": np.nan}

        signal, _ = sliding_window.to_array()

        # If multi-channel, compute for first channel only
        if signal.ndim > 1 and signal.shape[1] > 1:
            signal = signal[:, 0]

        filtered = self._filter_signal(signal.squeeze())
        normalized = normalize_signal(filtered)

        sparc = compute_sparc(normalized, self.rate_hz)
        jerk = compute_jerk_rms(filtered, self.rate_hz)

        return {"sparc": sparc, "jerk_rms": jerk}