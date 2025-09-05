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