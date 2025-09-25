import sys, os

if os.getcwd() not in sys.path:
    sys.path.append(os.getcwd())

from collections import deque

from pyeyesweb.data_models.sliding_window import SlidingWindow
from pyeyesweb.utils.signal_processing import bandpass_filter, compute_hilbert_phases
from pyeyesweb.utils.math_utils import compute_phase_locking_value, center_signals


class Synchronization:
    # Initialization of the Synchronization class with parameters for window size, sensitivity, phase output, and filter settings.
    def __init__(self, sensitivity=100, output_phase=False, filter_params=None, phase_threshold=0.7):
        self.plv_history = deque(maxlen=sensitivity)  # Buffer to keep track of the phase locking value (PLV) history.
        self.output_phase = output_phase  # Boolean to control whether phase status is output.
        self.filter_params = filter_params  # Parameters for the band-pass filter if filtering is needed.
        self.phase_threshold = phase_threshold  # Threshold for determining phase synchronization status.


    # Method to compute synchronization between the two signals using the Hilbert Transform.
    def compute_synchronization(self, signals: SlidingWindow):
        """Compute synchronization using the Hilbert Transform."""

        if not signals.is_full():
            return None, None

        sig, _ = signals.to_array()

        # Apply band-pass filtering if filter parameters are provided.
        sig = bandpass_filter(sig, self.filter_params)

        # Remove the mean from each signal to center the data.
        sig = center_signals(sig)

        # Extract the phase information from the analytic signals.
        phase1, phase2 = compute_hilbert_phases(sig)

        # Compute the Phase Locking Value (PLV).
        plv = compute_phase_locking_value(phase1, phase2)
        self.plv_history.append(plv)  # Store the PLV in the history buffer.

        phase_status = None
        if self.output_phase:
            # Use PLV (which is the same as MVL) to determine phase synchronization status.
            phase_status = "IN PHASE" if plv > self.phase_threshold else "OUT OF PHASE"

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
