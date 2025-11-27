import numpy as np

from pyeyesweb.data_models.sliding_window import SlidingWindow
from pyeyesweb.low_level.kinetic_energy import KineticEnergy
from pyeyesweb.analysis_primitives.rarity import Rarity
from pyeyesweb.utils.math_utils import (compute_sparc, compute_jerk_rms, normalize_signal, extract_velocity_from_position)
from pyeyesweb.utils.validators import validate_numeric, validate_boolean
from pyeyesweb.utils.signal_processing import apply_savgol_filter

class Lightness:


    sliding_window = SlidingWindow(50, 1)  # Store velocity values
    lightness = Rarity()

    def __init__(self, rate_hz=50.0, use_filter=True, signal_type='velocity'):
        self.rate_hz = validate_numeric(rate_hz, 'rate_hz', min_val=0.01, max_val=100000)
        self.use_filter = validate_boolean(use_filter, 'use_filter')

        # Validate signal_type
        if signal_type not in ['velocity', 'position']:
            raise ValueError(f"signal_type must be 'velocity' or 'position', got '{signal_type}'")
        self.signal_type = signal_type
        



    def _filter_signal(self, signal):
        """Apply Savitzky-Golay filter if enabled and enough data.

        Parameters
        ----------
        signal : array-like
            Input signal to filter.

        Returns
        -------
        ndarray
            Filtered signal or original if filtering disabled/not possible.
        """
        if not self.use_filter:
            return np.array(signal)
        return apply_savgol_filter(signal, self.rate_hz)

    def __call__(self, velocity, alpha: float = 0.5) -> dict:


        vel = np.array([velocity])

        ke = KineticEnergy()
        resultKE = ke(vel)

        # use total energy (scalar) rather than the whole dict
        weight_index =resultKE["component_energy"][1]/ resultKE["total_energy"]


        if not isinstance(weight_index, (float, np.floating)) or not np.isfinite(weight_index):
            weight_index = 0.0


        self.sliding_window.append([1.0-weight_index])   # ora sliding_window contiene floats
        
        resultLightness = self.lightness(self.sliding_window)    # Rarity riceve una sequenza di numeri
        return (resultLightness)
