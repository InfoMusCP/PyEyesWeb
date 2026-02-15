import numpy as np

from pyeyesweb.data_models.sliding_window import SlidingWindow
from pyeyesweb.low_level.kinetic_energy import KineticEnergy
from pyeyesweb.analysis_primitives.rarity import Rarity
from pyeyesweb.utils.validators import validate_numeric, validate_boolean
from pyeyesweb.utils.signal_processing import apply_savgol_filter


class Lightness:
    # sliding_window = SlidingWindow(50, 1)  # Store velocity values
    kinetic_energy = KineticEnergy()
    rarity = Rarity()

    def __init__(self, sliding_window_max_length=50.0, rate_hz=50.0, use_filter=True, signal_type='velocity'):
        self.sliding_window_max_length = validate_numeric(
            sliding_window_max_length,
            'sliding_window_max_length',
            min_val=1,
            max_val=100000
        )
        self.rate_hz = validate_numeric(rate_hz, 'rate_hz', min_val=0.01, max_val=100000)
        self.use_filter = validate_boolean(use_filter, 'use_filter')

        self.sliding_window = SlidingWindow(int(self.sliding_window_max_length), 1)

        # Validate signal_type
        if signal_type not in ['velocity', 'position']:
            raise ValueError(f"signal_type must be 'velocity' or 'position', got '{signal_type}'")
        self.signal_type = signal_type

    def __call__(self, velocity, alpha: float = 0.5) -> dict:

        vel = np.array([velocity])

        ke = self.kinetic_energy(vel)

        # use total energy (scalar) rather than the whole dict
        weight_index = ke["component_energy"][1] / (ke["total_energy"] + 1e-9)

        if not isinstance(weight_index, (float, np.floating)) or not np.isfinite(weight_index):
            weight_index = 0.0

        self.sliding_window.append([1.0 - weight_index])  # ora sliding_window contiene floats

        lightness = self.rarity(self.sliding_window, alpha=alpha)

        return {"lightness": lightness.get("rarity", 0), "weight_index": weight_index}

    def _filter_signal(self, signal):
        if not self.use_filter:
            return np.array(signal)
        return apply_savgol_filter(signal, self.rate_hz)
