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
from pyeyesweb.utils.signal_processing import compute_phase_synchronization
from pyeyesweb.utils.validators import validate_numeric, validate_and_normalize_filter_params


class Synchronization:
    """Real time phase synchronization analyzer for paired signals.

    This class computes the Phase Locking Value (PLV) between two signals
    using the Hilbert Transform to extract instantaneous phase information.
    It can optionally apply band-pass filtering to focus on specific frequency bands.

    The PLV ranges from 0 (no synchronization) to 1 (perfect synchronization)
    and is computed as the absolute value of the mean complex phase difference
    between the two signals.

    Read more in the [User Guide](/PyEyesWeb/user_guide/theoretical_framework/analysis_primitives/synchronization/)

    Parameters
    ----------
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
        If output_phase is not bool, phase_threshold
        is not numeric, or filter_params is not tuple/list.
    ValueError
        If phase_threshold outside [0, 1],
        or filter_params contains invalid frequencies.

    Attributes
    ----------
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

    def __init__(self, filter_params=None, phase_threshold=0.7):
        self.phase_threshold = validate_numeric(phase_threshold, 'phase_threshold', min_val=0, max_val=1)

        # validate and normalize filter params
        self.filter_params = validate_and_normalize_filter_params(filter_params)


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
            - 'value': Same as 'plv'.

        Output
        ------------
        Prints synchronization metrics to stdout if PLV is computed successfully.
        Format depends on output_phase setting.
        """
        if sliding_window.get_num_joints() < 2:
            raise ValueError("Synchronization analysis requires at least 2 signals (columns) in the sliding window.")
        values = sliding_window.to_array()[0]
        plv = compute_phase_synchronization(values, self.filter_params)
        return {"value": plv}


if __name__ == "__main__":
    import numpy as np
    from pythonosc.dispatcher import Dispatcher
    from pythonosc.osc_server import BlockingOSCUDPServer
    from pythonosc.udp_client import SimpleUDPClient
    from pyeyesweb.data_models.sliding_window import SlidingWindow
    from pyeyesweb.analysis_primitives.synchronization import Synchronization

    # Initialize Synchronization analyzer
    sync = Synchronization(filter_params=None, phase_threshold=0.8)
    max_len = 200
    window = SlidingWindow(max_length=max_len, n_dimensions=2, m_joints=2)
    sig1 = np.sin(2 * np.pi * 5 * np.linspace(0, 1, max_len*100))  # 5 Hz sine wave
    sig2 = np.sin(2 * np.pi * 5 * np.linspace(0, 1, max_len*100) + np.pi / 4)  # Same frequency, phase shifted
    
    sig3 = np.array(list(zip(sig1, sig2)))
    sig4 = np.array(list(zip(sig2, sig1)))
    for i in range(max_len*100):
        window.append([sig3[i], sig3[i]])
        if window.is_full():
            result = sync(window)
            print(f"PLV: {result['value']:.3f}")