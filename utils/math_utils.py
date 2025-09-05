import numpy as np


def compute_phase_locking_value(phase1, phase2):
    """Compute the Phase Locking Value (PLV) from two phase arrays."""
    phase_diff = phase1 - phase2
    phase_diff_exp = np.exp(1j * phase_diff)
    plv = np.abs(np.mean(phase_diff_exp))
    return plv


def center_signals(sig):
    """Remove the mean from each signal to center the data."""
    return sig - np.mean(sig, axis=0, keepdims=True)


def compute_sparc(signal, rate_hz=50.0):
    """Compute SPARC (Spectral Arc Length) from a signal."""
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
    """Compute RMS of jerk (third derivative) from a signal."""
    if len(signal) < 2:
        return float("nan")
    dt = 1.0 / rate_hz
    jerk = np.diff(signal) / dt
    return np.sqrt(np.mean(jerk ** 2))


def normalize_signal(signal):
    """Normalize signal by its maximum absolute value."""
    max_val = np.max(np.abs(signal))
    return signal / max_val if max_val != 0 else signal