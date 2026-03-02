"""Signal processing utilities for PyEyesWeb.

This module provides signal processing functions including filtering,
phase extraction, and smoothing operations used throughout the library.
"""

import numpy as np
from scipy.signal import hilbert, butter, filtfilt, savgol_filter
from pyeyesweb.utils.math_utils import center_signals, compute_phase_locking_value

# ADDED THIS IMPORT:
from pyeyesweb.utils.validators import validate_filter_params_tuple


def validate_filter_params(lowcut, highcut, fs):
    """Validate filter frequency parameters.

    Centralized validation for filter parameters used in bandpass_filter
    and Synchronization class.
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


def validate_and_normalize_filter_params(filter_params):
    """Validate and normalize filter parameters.

    Parameters
    ----------
    filter_params : tuple/list or None
        Filter parameters as (lowcut, highcut, fs) or None

    Returns
    -------
    tuple or None
        Validated (lowcut, highcut, fs) tuple or None if input was None
    """
    if filter_params is None:
        return None

    filter_params = validate_filter_params_tuple(filter_params)
    lowcut, highcut, fs = validate_filter_params(*filter_params)
    return lowcut, highcut, fs


def bandpass_filter(data, filter_params):
    """Apply a band-pass filter if filter_params is set."""
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
    """Compute phase information from signals using Hilbert Transform."""
    analytic_signal1 = hilbert(sig[:, 0])
    analytic_signal2 = hilbert(sig[:, 1])

    phase1 = np.angle(analytic_signal1)
    phase2 = np.angle(analytic_signal2)

    return phase1, phase2


def compute_phase_synchronization(signals, filter_params=None):
    """Compute phase synchronization between two signals."""
    sig = bandpass_filter(signals, filter_params)
    sig = center_signals(sig)
    phase1, phase2 = compute_hilbert_phases(sig)

    return compute_phase_locking_value(phase1, phase2)


def apply_savgol_filter(signal, rate_hz=50.0):
    """Apply Savitzky-Golay filter if enough data is available."""
    if len(signal) < 5:
        return np.array(signal)

    N = len(signal)
    polyorder = 3
    window_length = min(N if N % 2 == 1 else N - 1, 11)
    if window_length <= polyorder:
        return np.array(signal)

    try:
        return savgol_filter(signal, window_length=window_length, polyorder=polyorder)
    except Exception:
        return np.array(signal)