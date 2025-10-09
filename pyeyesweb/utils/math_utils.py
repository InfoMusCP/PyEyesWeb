"""Mathematical utility functions for signal analysis.

This module provides mathematical functions used throughout the PyEyesWeb
library for signal processing, phase analysis, and movement metrics.
"""

import numpy as np
from pyeyesweb.utils.validators import validate_numeric

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

    This implementation is based on the original algorithm by Balasubramanian et al. (2015).
    SPARC values are typically negative, with values closer to 0 indicating less smooth
    (more complex) movements. For healthy reaching movements, values around -1.4 to -1.6
    are common. Pathological or very unsmooth movements may have values ranging from
    -3 to -10 or lower, depending on the degree of movement fragmentation.

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
    Balasubramanian, S., Melendez-Calderon, A., Roby-Brami, A., & Burdet, E. (2015).
    On the analysis of movement smoothness. Journal of NeuroEngineering and Rehabilitation,
    12(1), 1-11.
    """
    rate_hz = validate_numeric(rate_hz, 'rate_hz', min_val=0.0001)

    # Ensure signal is 1D
    signal = np.asarray(signal)
    if signal.ndim > 1:
        # If 2D, check if it's a single column/row
        if signal.shape[0] == 1:
            signal = signal.flatten()
        elif signal.shape[1] == 1:
            signal = signal.flatten()
        else:
            raise ValueError(f"Signal must be 1D, got shape {signal.shape}")

    N = len(signal)
    if N < 2:
        return np.nan

    # Check if signal is constant (no movement)
    if np.allclose(signal, signal[0]):
        # For constant signals, return NaN as SPARC is undefined
        # (no movement means smoothness is not applicable)
        return np.nan

    from scipy.fft import fft, fftfreq
    yf = np.abs(fft(signal))[:N // 2]
    xf = fftfreq(N, 1.0 / rate_hz)[:N // 2]

    # Normalize magnitude by maximum value
    max_yf = np.max(yf)
    if max_yf > 0:
        yf /= max_yf
    else:
        # This should not happen after the constant signal check
        # but keep as safety fallback
        return np.nan

    # Compute arc length with normalized frequency differences
    # Following Balasubramanian et al. (2015) implementation
    freq_range = xf[-1] - xf[0]
    if freq_range <= 0:
        return np.nan

    # Normalize frequency differences by the frequency range
    arc = np.sum(np.sqrt((np.diff(xf) / freq_range)**2 + np.diff(yf)**2))
    return -arc


def compute_jerk_rms(signal, rate_hz=50.0, signal_type='velocity'):
    """Compute RMS of jerk (rate of change of acceleration) from a signal.

    Jerk is the third derivative of position or the first derivative of acceleration. Lower RMS jerk values indicate smoother movement.

    Parameters
    ----------
    signal : ndarray
        1D movement signal.
    rate_hz : float, optional
        Sampling rate in Hz (default: 50.0).
    signal_type : str, optional
        Type of input signal: 'position' or 'velocity' (default: 'velocity').
        - 'position': Computes third derivative to get jerk
        - 'velocity': Computes second derivative to get jerk

    Returns
    -------
    float
        Root mean square of jerk.
        Returns NaN if signal has insufficient samples for the required derivatives.

    Notes
    -----
    Uses numpy.gradient for smooth derivative approximation with central differences
    where possible, providing better accuracy than forward differences.
    """
    rate_hz = validate_numeric(rate_hz, 'rate_hz', min_val=0.0001)

    # Define derivative orders needed for each signal type
    derivative_orders = {
        'velocity': 2,  # if signal type is velocity we can get velocity -> acceleration -> jerk
        'position': 3   # if signal type is position we can get position -> velocity -> acceleration -> jerk
    }

    if signal_type not in derivative_orders:
        raise ValueError(f"signal_type must be 'position' or 'velocity', got '{signal_type}'")

    n_derivatives = derivative_orders[signal_type]
    min_samples = n_derivatives + 1

    if len(signal) < min_samples:
        return np.nan

    # Apply derivatives using numpy.gradient for better accuracy
    result = np.asarray(signal)
    for _ in range(n_derivatives):
        result = np.gradient(result, 1.0/rate_hz)

    return np.sqrt(np.mean(result ** 2))


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


def extract_velocity_from_position(position, rate_hz=50.0):
    """Extract velocity from position data.

    Computes velocity magnitude from position data of any dimensionality.
    For 1D position, returns absolute velocity. For multi-dimensional position,
    returns the Euclidean norm of the velocity vector.

    Parameters
    ----------
    position : ndarray
        Position data. Can be:
        - 1D array: single position coordinate
        - 2D array with shape (n_samples, n_dims): multi-dimensional positions
    rate_hz : float, optional
        Sampling rate in Hz (default: 50.0).

    Returns
    -------
    ndarray
        1D array of velocity magnitudes.

    Examples
    --------
    >>> # 1D position data
    >>> position_1d = np.array([0, 1, 2, 3, 4])
    >>> velocity = extract_velocity_from_position(position_1d, rate_hz=100)

    >>> # 2D position data (x, y coordinates)
    >>> position_2d = np.array([[0, 0], [1, 0], [1, 1], [2, 1]])
    >>> velocity = extract_velocity_from_position(position_2d, rate_hz=100)
    """
    rate_hz = validate_numeric(rate_hz, 'rate_hz', min_val=0.0001)
    dt = 1.0 / rate_hz

    position = np.asarray(position)

    # Handle 1D position
    if position.ndim == 1 or (position.ndim == 2 and position.shape[1] == 1):
        signal_1d = position.squeeze()
        return np.abs(np.gradient(signal_1d, dt))

    # Handle multi-dimensional position
    if position.ndim == 2:
        # Compute derivatives along time axis (axis=0)
        derivatives = np.gradient(position, dt, axis=0)
        # Return Euclidean norm of velocity vector
        return np.linalg.norm(derivatives, axis=1)

    raise ValueError(f"Position must be 1D or 2D array, got shape {position.shape}")