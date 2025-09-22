import numpy as np
from scipy.signal import hilbert, butter, filtfilt


def bandpass_filter(data, filter_params):
    """Apply a band-pass filter if filter_params is set."""
    if filter_params is None:
        return data

    lowcut, highcut, fs = filter_params
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
        from scipy.signal import savgol_filter
        return savgol_filter(signal, window_length=window_length, polyorder=polyorder)
    except Exception:
        return np.array(signal)