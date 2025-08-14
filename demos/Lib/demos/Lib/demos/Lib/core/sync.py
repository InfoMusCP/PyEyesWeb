import sys, os

if os.getcwd() not in sys.path:
    sys.path.append(os.getcwd())

from core.data_models.sliding_window import SlidingWindow
import numpy as np
from collections import deque
from scipy.signal import hilbert, butter, filtfilt


class Synchronization:
    # Initialization of the Synchronization class with parameters for window size, sensitivity, phase output, and filter settings.
    def __init__(self, sensitivity=100, output_phase=False, filter_params=None):
        self.plv_history = deque(maxlen=sensitivity)  # Buffer to keep track of the phase locking value (PLV) history.
        self.output_phase = output_phase  # Boolean to control whether phase status is output.
        self.filter_params = filter_params  # Parameters for the band-pass filter if filtering is needed.

    # Method to apply a band-pass filter to the input data based on the filter parameters provided during initialization.
    def bandpass_filter(self, data):
        """Apply a band-pass filter if filter_params is set."""
        if self.filter_params is None:
            return data  # If no filter parameters are set, return the data as is.

        # Low cut-off frequency, high cut-off frequency, and sampling rate.
        lowcut, highcut, fs = self.filter_params
        nyquist = 0.5 * fs  # Nyquist frequency is half of the sampling rate.
        low = lowcut / nyquist  # Normalizing the low cut-off frequency.
        high = highcut / nyquist  # Normalizing the high cut-off frequency.

        # Designing a 4th-order Butterworth band-pass filter.
        b, a = butter(4, [low, high], btype='band')

        # Filter each column independently
        filtered_data = np.zeros_like(data)
        for i in range(data.shape[1]):
            filtered_data[:, i] = filtfilt(b, a, data[:, i])

        return filtered_data

    # Method to compute synchronization between the two signals using the Hilbert Transform.
    def compute_synchronization(self, signals: SlidingWindow):
        """Compute synchronization using the Hilbert Transform."""

        if not signals.is_full():
            return None, None

        sig, _ = signals.to_array()

        # Apply band-pass filtering if filter parameters are provided.
        sig = self.bandpass_filter(sig)

        # Remove the mean from each signal to center the data.
        sig[:, 0] -= np.mean(sig[:, 0])
        sig[:, 1] -= np.mean(sig[:, 1])

        # Apply the Hilbert Transform to obtain the analytic signal, which provides both amplitude and phase information.
        analytic_signal1 = hilbert(sig[:, 0])
        analytic_signal2 = hilbert(sig[:, 1])

        # Extract the phase information from the analytic signals.
        phase1 = np.angle(analytic_signal1)
        phase2 = np.angle(analytic_signal2)

        # Compute the phase difference between the two signals.
        phase_diff = phase1 - phase2

        # Ensure the phase difference is wrapped between -π and π.
        phase_diff = np.arctan2(np.sin(phase_diff), np.cos(phase_diff))

        # Convert the phase difference to a complex exponential and compute the Phase Locking Value (PLV).
        phase_diff_exp = np.exp(1j * phase_diff)
        plv = np.abs(np.sum(phase_diff_exp)) / len(signals)  # PLV is the magnitude of the average phase difference.
        self.plv_history.append(plv)  # Store the PLV in the history buffer.

        phase_status = None
        if self.output_phase:
            # Compute the Mean Vector Length (MVL) to determine phase synchronization status.
            mvl = np.abs(np.mean(phase_diff_exp))
            phase_status = "IN PHASE" if mvl > 0.7 else "OUT OF PHASE"

        return plv, phase_status  # Return the computed PLV and phase status.

    def __call__(self, sliding_window: SlidingWindow):
        plv, phase_status = self.compute_synchronization(sliding_window)

        if plv is not None:
            if self.output_phase:
                # Print the synchronization index and phase status if output_phase is True.
                print(f"Synchronization Index: {plv:.3f}, Phase Status: {phase_status}")
            else:
                # Print only the synchronization index if output_phase is False.
                print(f"Synchronization Index: {plv:.3f}")
        return plv, phase_status  # Return the computed values.
