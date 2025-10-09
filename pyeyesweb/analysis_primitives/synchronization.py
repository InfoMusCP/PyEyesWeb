"""Synchronization analysis module for real time signal phase locking.

This module provides tools for computing phase synchronization between paired
signals using the Hilbert Transform and Phase Locking Value (PLV) analysis.
It is designed for real time analysis of motion capture or sensor data streams.

The synchronization analysis follows these steps:
1. Optional band pass filtering to isolate frequencies of interest
2. Signal centering (mean removal) to eliminate DC bias
3. Hilbert Transform to extract instantaneous phase information
4. Phase Locking Value computation to quantify synchronization strength

Typical use cases include:
1. Movement coordination analysis between limbs
2. Human-human or human-robot interaction studies
3. Neural oscillation synchronization
4. Periodic signal coupling analysis

References
----------
1. Lachaux et al. (1999). Measuring phase synchrony in brain signals.
  Human Brain Mapping, 8(4), 194-208.
2. Rosenblum et al. (1996). Phase synchronization of chaotic oscillators.
  Physical Review Letters, 76(11), 1804.
"""

import numpy as np

from pyeyesweb.data_models.sliding_window import SlidingWindow
from pyeyesweb.data_models.thread_safe_buffer import ThreadSafeHistoryBuffer
from pyeyesweb.utils.signal_processing import compute_phase_synchronization
from pyeyesweb.utils.validators import validate_integer, validate_boolean, validate_numeric, validate_and_normalize_filter_params


class Synchronization:
    """Real time phase synchronization analyzer for paired signals.

    This class computes the Phase Locking Value (PLV) between two signals
    using the Hilbert Transform to extract instantaneous phase information.
    It maintains a history buffer for tracking synchronization over time and
    can optionally apply band-pass filtering to focus on specific frequency bands.

    The PLV ranges from 0 (no synchronization) to 1 (perfect synchronization)
    and is computed as the absolute value of the mean complex phase difference
    between the two signals.

    Read more in the [User Guide](/PyEyesWeb/user_guide/theoretical_framework/analysis_primitives/synchronization/)

    Parameters
    ----------
    sensitivity : int, optional
        Size of the PLV history buffer. Larger values provide more temporal
        context but increase memory usage. Must be positive integer between
        1 and 10,000 (default: 100).
    output_phase : bool, optional
        If True, outputs phase synchronization status as "IN PHASE" or
        "OUT OF PHASE" based on the phase_threshold. Must be boolean
        (default: False).
    filter_params : tuple of (float, float, float) or None, optional
        Band-pass filter parameters as (lowcut_hz, highcut_hz, sampling_rate_hz).
        All frequencies must be positive with lowcut < highcut < sampling_rate/2.
        Example: (0.5, 30, 100) for 0.5-30 Hz band with 100 Hz sampling.
        If None, no filtering is applied (default: None).
    phase_threshold : float, optional
        PLV threshold for phase status determination. Values above this are
        considered "IN PHASE". Must be between 0 and 1 inclusive (default: 0.7).

    Raises
    ------
    TypeError
        If sensitivity is not int, output_phase is not bool, phase_threshold
        is not numeric, or filter_params is not tuple/list.
    ValueError
        If sensitivity <= 0 or > 10,000, phase_threshold outside [0, 1],
        or filter_params contains invalid frequencies.

    Attributes
    ----------
    plv_history : ThreadSafeHistoryBuffer
        Thread-safe rolling buffer storing recent PLV values for temporal analysis.
    output_phase : bool
        Flag controlling phase status output.
    filter_params : tuple or None
        Band-pass filter configuration.
    phase_threshold : float
        Threshold for phase synchronization classification.

    Examples
    --------
    >>> from pyeyesweb.analysis_primitives.synchronization import Synchronization
    >>> from pyeyesweb.data_models.sliding_window import SlidingWindow
    >>>
    >>> # Create synchronization analyzer with filtering
    >>> sync = Synchronization(
    ...     sensitivity=50,
    ...     output_phase=True,
    ...     filter_params=(1.0, 10.0, 100.0),  # 1-10 Hz band at 100 Hz
    ...     phase_threshold=0.8
    ... )
    >>>
    >>> # Create sliding window for two signals
    >>> window = SlidingWindow(max_length=200, n_columns=2)
    >>>
    >>> # Add signal data (e.g., from two sensors)
    >>> for i in range(200):
    ...     window.append([signal1[i], signal2[i]])
    >>>
    >>> # Compute synchronization
    >>> result = sync(window)
    >>> print(f"PLV: {result['plv']:.3f}, Status: {result['phase_status']}")

    Notes
    -----
    - Requires at least a full window of data to compute meaningful results
    - The Hilbert Transform assumes narrowband or filtered signals for best results
    - Phase differences are most meaningful for signals with similar frequencies
    - For broadband signals, consider using filter_params to isolate frequency bands
    """

    def __init__(self, sensitivity=100, output_phase=False, filter_params=None, phase_threshold=0.7):
        sensitivity = validate_integer(sensitivity, 'sensitivity', min_val=1, max_val=10000)
        self.output_phase = validate_boolean(output_phase, 'output_phase')
        self.phase_threshold = validate_numeric(phase_threshold, 'phase_threshold', min_val=0, max_val=1)

        # validate and normalize filter params
        self.filter_params = validate_and_normalize_filter_params(filter_params)

        # Use ThreadSafeHistoryBuffer instead of deque + lock
        self.plv_history = ThreadSafeHistoryBuffer(maxlen=sensitivity)


    def compute_synchronization(self, signals: SlidingWindow):
        """Compute phase synchronization between two signals.

        Processes the signal pair through filtering (optional), centering,
        Hilbert Transform, and PLV computation to quantify synchronization.

        Parameters
        ----------
        signals : SlidingWindow
            Sliding window buffer containing exactly 2 columns of signal data.
            Must be full (contain max_length samples) for computation.

        Returns
        -------
        dict
            Dictionary containing synchronization metrics:
            - 'plv': Phase Locking Value between 0 (no sync) and 1 (perfect sync).
                    Returns NaN if the window is not full.
            - 'phase_status': If output_phase is True, returns "IN PHASE" when PLV > phase_threshold,
                            "OUT OF PHASE" otherwise. Returns None if output_phase is False or
                            if the window is not full.

        Notes
        -----
        The computation pipeline:
        1. Check if window has sufficient data (is_full)
        2. Apply band-pass filter if filter_params is set
        3. Center signals by removing mean (eliminates DC component)
        4. Apply Hilbert Transform to get analytic signal and phase
        5. Compute PLV from phase difference
        6. Update PLV history buffer
        7. Determine phase status if requested
        """
        # Validate input has exactly 2 columns
        if signals._n_columns != 2:
            raise ValueError(f"Synchronization requires exactly 2 signal channels, got {signals._n_columns}")

        if not signals.is_full():
            return {"plv": np.nan, "phase_status": None}

        sig, _ = signals.to_array()

        # combines all phase sync steps
        plv = compute_phase_synchronization(sig, self.filter_params)

        self.plv_history.append(plv)

        phase_status = None
        if self.output_phase:
            # Determine phase synchronization status based on threshold
            phase_status = "IN PHASE" if plv > self.phase_threshold else "OUT OF PHASE"

        return {"plv": plv, "phase_status": phase_status}

    def __call__(self, sliding_window: SlidingWindow):
        """Compute and optionally display synchronization metrics.

        This method allows the class to be used as a callable, providing a convenient interface for real time processing pipelines.

        Parameters
        ----------
        sliding_window : SlidingWindow
            Buffer containing two signal columns to analyze.

        Returns
        -------
        dict
            Dictionary containing synchronization metrics:
            - 'plv': Phase Locking Value (0-1) or NaN if insufficient data.
            - 'phase_status': Phase status ("IN PHASE"/"OUT OF PHASE") or None.

        Output
        ------------
        Prints synchronization metrics to stdout if PLV is computed successfully.
        Format depends on output_phase setting.
        """
        result = self.compute_synchronization(sliding_window)
        plv = result["plv"]
        phase_status = result["phase_status"]

        if not np.isnan(plv):
            if self.output_phase:
                print(f"Synchronization Index: {plv:.3f}, Phase Status: {phase_status}")
            else:
                print(f"Synchronization Index: {plv:.3f}")
        return result
