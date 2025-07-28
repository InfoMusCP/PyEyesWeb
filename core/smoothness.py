import numpy as np
from collections import deque
from scipy.signal import savgol_filter
from scipy.fft import fft, fftfreq

class Smoothness:
    def __init__(self, window_size=50, rate_hz=50.0, use_filter=True):
        self.window_size = window_size
        self.rate_hz = rate_hz
        self.use_filter = use_filter
        self.data = deque(maxlen=window_size)

    def add_data(self, point):
        self.data.append(point)

    def _filter_signal(self, signal):
        """Apply Savitzky-Golay filter if enabled and enough data."""
        if not self.use_filter or len(signal) < 5:
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

    def compute_sparc(self, signal):
        N = len(signal)
        if N < 2:
            return float("nan")
        yf = np.abs(fft(signal))[:N // 2]
        xf = fftfreq(N, 1.0 / self.rate_hz)[:N // 2]

        yf /= np.max(yf) if np.max(yf) != 0 else 1.0
        arc = np.sum(np.sqrt(np.diff(xf)**2 + np.diff(yf)**2))
        return -arc

    def compute_jerk_rms(self, signal):
        if len(signal) < 2:
            return float("nan")
        dt = 1.0 / self.rate_hz
        jerk = np.diff(signal) / dt
        return np.sqrt(np.mean(jerk ** 2))

    def process(self):
        if len(self.data) < 5:
            return None, None

        signal = np.array(self.data, dtype=np.float64)
        filtered = self._filter_signal(signal)

        max_val = np.max(np.abs(filtered))
        normalized = filtered / max_val if max_val != 0 else filtered

        sparc = self.compute_sparc(normalized)
        jerk = self.compute_jerk_rms(filtered)

        print(f"SPARC: {sparc:.3f}, Jerk RMS: {jerk:.3f}")
        return sparc, jerk
