import sys, os

if os.getcwd() not in sys.path:
    sys.path.append(os.getcwd())
import numpy as np
from collections import deque
from scipy.signal import hilbert, butter, filtfilt

class Synchronization:
    # Initialization of the Synchronization class with parameters for window size, sensitivity, phase output, and filter settings.
    def __init__(self, window_size=30, sensitivity=100, output_phase=False, filter_params=None):
        self.window_size = window_size  # Length of the time series window for synchronization calculation.
        self.signal1 = deque(maxlen=window_size)  # Time series buffer for the first signal.
        self.signal2 = deque(maxlen=window_size)  # Time series buffer for the second signal.
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
        return filtfilt(b, a, data)  # Applying the filter using forward-backward filtering to avoid phase shift.

    # Method to add new data points to the signal buffers.
    def add_data(self, point1, point2):
        """Add data points to the time series."""
        self.signal1.append(point1)  # Append the new point to the first signal buffer.
        self.signal2.append(point2)  # Append the new point to the second signal buffer.

    # Method to compute synchronization between the two signals using the Hilbert Transform.
    def compute_synchronization(self):
        """Compute synchronization using the Hilbert Transform."""
        # Ensure both signals have enough data points for the computation.
        if len(self.signal1) < self.window_size or len(self.signal2) < self.window_size:
            return None, None  # Return None if the window is not yet full.

        # Convert signal buffers to NumPy arrays for processing.
        sig1 = np.array(self.signal1, dtype=np.float64)
        sig2 = np.array(self.signal2, dtype=np.float64)

        # Apply band-pass filtering if filter parameters are provided.
        sig1 = self.bandpass_filter(sig1)
        sig2 = self.bandpass_filter(sig2)

        # Remove the mean from each signal to center the data.
        sig1 -= np.mean(sig1)
        sig2 -= np.mean(sig2)

        # Apply the Hilbert Transform to obtain the analytic signal, which provides both amplitude and phase information.
        analytic_signal1 = hilbert(sig1)
        analytic_signal2 = hilbert(sig2)

        # Extract the phase information from the analytic signals.
        phase1 = np.angle(analytic_signal1)
        phase2 = np.angle(analytic_signal2)

        # Compute the phase difference between the two signals.
        phase_diff = phase1 - phase2

        # Ensure the phase difference is wrapped between -π and π.
        phase_diff = np.arctan2(np.sin(phase_diff), np.cos(phase_diff))

        # Convert the phase difference to a complex exponential and compute the Phase Locking Value (PLV).
        phase_diff_exp = np.exp(1j * phase_diff)
        plv = np.abs(np.sum(phase_diff_exp)) / self.window_size  # PLV is the magnitude of the average phase difference.
        self.plv_history.append(plv)  # Store the PLV in the history buffer.

        phase_status = None
        if self.output_phase:
            # Compute the Mean Vector Length (MVL) to determine phase synchronization status.
            mvl = np.abs(np.mean(phase_diff_exp))
            phase_status = "IN PHASE" if mvl > 0.7 else "OUT OF PHASE"

        return plv, phase_status  # Return the computed PLV and phase status.

    # Method to add new data points and compute synchronization in a single step.
    def process(self, point1, point2):
        """Add data and compute synchronization index and phase status."""
        self.add_data(point1, point2)  # Add new data points to the buffers.
        plv, phase_status = self.compute_synchronization()  # Compute synchronization metrics.
        if plv is not None:
            if self.output_phase:
                # Print the synchronization index and phase status if output_phase is True.
                print(f"Synchronization Index: {plv:.3f}, Phase Status: {phase_status}")
            else:
                # Print only the synchronization index if output_phase is False.
                print(f"Synchronization Index: {plv:.3f}")
        return plv, phase_status  # Return the computed values.

# Main execution block to test the synchronization class.
if __name__ == "__main__":
    # Test with synchronized signals (same frequency).
    sync = Synchronization(window_size=30, output_phase=True)
    print("Testing synchronized signals:")
    for i in range(100):
        point1 = np.sin(2 * np.pi * i / 50)  # Sine wave with a specific frequency.
        point2 = np.sin(2 * np.pi * i / 50)  # Sine wave with the same frequency.
        sync.process(point1, point2)

    print("\nTesting unsynchronized signals:")
    # Test with unsynchronized signals (different frequencies).
    sync = Synchronization(window_size=30, output_phase=True)
    for i in range(100):
        point1 = np.sin(2 * np.pi * i / 50)  # Sine wave with one frequency.
        point2 = np.sin(2 * np.pi * i / 30)  # Sine wave with a different frequency.
        sync.process(point1, point2)