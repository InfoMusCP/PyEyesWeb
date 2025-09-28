"""Mathematical utility functions for signal analysis.

This module provides mathematical functions used throughout the PyEyesWeb
library for signal processing, phase analysis, and movement metrics.
"""

import numpy as np

def compute_phase_locking_value(phase1, phase2):
    """Compute the Phase Locking Value (PLV) from two phase arrays.

    PLV measures the inter-trial variability of the phase difference between
    two signals. A value of 1 indicates perfect phase locking, while 0
    indicates no phase relationship.

    Parameters
    ----------
    phase1 : ndarray
        Phase values of first signal in radians.
    phase2 : ndarray
        Phase values of second signal in radians.

    Returns
    -------
    float
        Phase Locking Value between 0 and 1.

    References
    ----------
    Lachaux et al. (1999). Measuring phase synchrony in brain signals.
    """
    phase_diff = phase1 - phase2
    phase_diff_exp = np.exp(1j * phase_diff)
    plv = np.abs(np.mean(phase_diff_exp))
    return plv


def center_signals(sig):
    """Remove the mean from each signal to center the data.

    Centers signals by subtracting the mean, removing DC bias.

    Parameters
    ----------
    sig : ndarray
        Signal array of shape (n_samples, n_channels).

    Returns
    -------
    ndarray
        Centered signal with same shape as input.
    """
    return sig - np.mean(sig, axis=0, keepdims=True)


def compute_sparc(signal, rate_hz=50.0):
    """Compute SPARC (Spectral Arc Length) from a signal.

    SPARC is a dimensionless smoothness metric that quantifies movement
    smoothness independent of movement amplitude and duration. More negative
    values indicate smoother movement.

    Parameters
    ----------
    signal : ndarray
        1D movement signal.
    rate_hz : float, optional
        Sampling rate in Hz (default: 50.0).

    Returns
    -------
    float
        SPARC value (negative, more negative = smoother).
        Returns NaN if signal has less than 2 samples.

    References
    ----------
    Balasubramanian et al. (2015). On the analysis of movement smoothness from the Journal of NeuroEngineering and Rehabilitation.
    """
    N = len(signal)
    if N < 2:
        return float("nan")
    
    from scipy.fft import fft, fftfreq
    yf = np.abs(fft(signal))[:N // 2]
    xf = fftfreq(N, 1.0 / rate_hz)[:N // 2]

    yf /= np.max(yf) if np.max(yf) != 0 else 1.0
    arc = np.sum(np.sqrt(np.diff(xf)**2 + np.diff(yf)**2))
    return -arc


def compute_jerk_rms(signal, rate_hz=50.0):
    """Compute RMS of jerk (third derivative) from a signal.

    Jerk is the rate of change of acceleration. Lower RMS jerk values
    indicate smoother movement.

    Parameters
    ----------
    signal : ndarray
        1D movement signal (position or velocity).
    rate_hz : float, optional
        Sampling rate in Hz (default: 50.0).

    Returns
    -------
    float
        Root mean square of jerk.
        Returns NaN if signal has less than 2 samples.

    Notes
    -----
    This implementation uses first-order finite differences to approximate
    the derivative. For position signals, this computes jerk directly.
    """
    if len(signal) < 2:
        return float("nan")
    dt = 1.0 / rate_hz
    jerk = np.diff(signal) / dt
    return np.sqrt(np.mean(jerk ** 2))


def normalize_signal(signal):
    """Normalize signal by its maximum absolute value.

    Scales the signal to the range [-1, 1] by dividing by the maximum
    absolute value.

    Parameters
    ----------
    signal : ndarray
        Input signal to normalize.

    Returns
    -------
    ndarray
        Normalized signal with same shape as input.
        Returns original signal if max absolute value is 0.
    """
    max_val = np.max(np.abs(signal))
    return signal / max_val if max_val != 0 else signal