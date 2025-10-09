"""Signal processing utilities for PyEyesWeb.

This module provides signal processing functions including filtering,
phase extraction, and smoothing operations used throughout the library.
"""

import numpy as np
from scipy.signal import hilbert, butter, filtfilt


def validate_filter_params(lowcut, highcut, fs):
    """Validate filter frequency parameters.

    Centralized validation for filter parameters used in bandpass_filter
    and Synchronization class.

    Parameters
    ----------
    lowcut : float
        Low cutoff frequency in Hz
    highcut : float
        High cutoff frequency in Hz
    fs : float
        Sampling frequency in Hz

    Returns
    -------
    tuple
        Validated (lowcut, highcut, fs)

    Raises
    ------
    ValueError
        If parameters are invalid
    """
    # Validate individual parameters
    if fs <= 0:
        raise ValueError(f"Sampling frequency must be positive, got {fs}")
    if lowcut <= 0:
        raise ValueError(f"Low cutoff frequency must be positive, got {lowcut}")
    if highcut <= 0:
        raise ValueError(f"High cutoff frequency must be positive, got {highcut}")

    # Validate relationships
    if lowcut >= highcut:
        raise ValueError(f"Low cutoff ({lowcut}) must be less than high cutoff ({highcut})")

    nyquist = fs / 2
    if highcut >= nyquist:
        raise ValueError(f"High cutoff ({highcut}) must be less than Nyquist frequency ({nyquist})")

    return lowcut, highcut, fs


def bandpass_filter(data, filter_params):
    """Apply a band-pass filter if filter_params is set.

    Uses a 4th order Butterworth band-pass filter with zero-phase
    filtering (filtfilt) to avoid phase distortion.

    Parameters
    ----------
    data : ndarray
        Signal data of shape (n_samples, n_channels).
    filter_params : tuple of (float, float, float) or None
        Filter parameters as (lowcut_hz, highcut_hz, sampling_rate_hz).
        If None, returns data unchanged.

    Returns
    -------
    ndarray
        Filtered data with same shape as input.
        Returns original data if filter_params is None.

    Examples
    --------
    >>> data = np.random.randn(1000, 2)  # 2 channels, 1000 samples
    >>> filtered = bandpass_filter(data, (1.0, 10.0, 100.0))  # 1-10 Hz
    """
    if filter_params is None:
        return data

    lowcut, highcut, fs = validate_filter_params(*filter_params)

    nyquist = 0.5 * fs
    low = lowcut / nyquist
    high = highcut / nyquist

    b, a = butter(4, [low, high], btype='band')

    filtered_data = np.zeros_like(data)
    for i in range(data.shape[1]):
        filtered_data[:, i] = filtfilt(b, a, data[:, i])

    return filtered_data


def compute_hilbert_phases(sig):
    """Compute phase information from signals using Hilbert Transform.

    The Hilbert transform creates an analytic signal from which instantaneous
    phase can be extracted. Assumes input has exactly 2 channels.

    Parameters
    ----------
    sig : ndarray
        Signal array of shape (n_samples, 2) with two channels.

    Returns
    -------
    phase1 : ndarray
        Phase values for first channel in radians [-π, π].
    phase2 : ndarray
        Phase values for second channel in radians [-π, π].

    Notes
    -----
    The Hilbert transform assumes the signal is narrowband or has been
    appropriately filtered for meaningful phase extraction.
    """
    analytic_signal1 = hilbert(sig[:, 0])
    analytic_signal2 = hilbert(sig[:, 1])
    
    phase1 = np.angle(analytic_signal1)
    phase2 = np.angle(analytic_signal2)
    
    return phase1, phase2


def compute_phase_synchronization(signals, filter_params=None):
    """Compute phase synchronization between two signals.

    Parameters
    ----------
    signals : ndarray
        Array of shape (n_samples, 2) containing two signals
    filter_params : tuple or None
        Optional filter parameters (lowcut, highcut, fs)

    Returns
    -------
    float
        Phase Locking Value between 0 and 1
    """
    from pyeyesweb.utils.math_utils import center_signals, compute_phase_locking_value
    
    sig = bandpass_filter(signals, filter_params)
    sig = center_signals(sig)
    phase1, phase2 = compute_hilbert_phases(sig)

    return compute_phase_locking_value(phase1, phase2)


def apply_savgol_filter(signal, rate_hz=50.0):
    """Apply Savitzky-Golay filter if enough data is available.

    Savitzky-Golay filtering smooths data while preserving features better
    than moving average filters. Uses polynomial order 3 and adaptive
    window length.

    Parameters
    ----------
    signal : array-like
        1D signal to filter.
    rate_hz : float, optional
        Sampling rate in Hz (currently unused but kept for API compatibility).

    Returns
    -------
    ndarray
        Filtered signal if sufficient data (≥5 samples), otherwise original
        signal as array. Window length is min(n_samples, 11) and must be odd.

    Notes
    -----
    - Requires at least 5 samples for filtering
    - Window length must exceed polynomial order (3)
    - Returns original signal if filtering fails
    """
    if len(signal) < 5:
        return np.array(signal)

    N = len(signal)
    polyorder = 3
    window_length = min(N if N % 2 == 1 else N - 1, 11)
    if window_length <= polyorder:
        return np.array(signal)

    try:
        from scipy.signal import savgol_filter
        return savgol_filter(signal, window_length=window_length, polyorder=polyorder)
    except Exception:
        return np.array(signal)