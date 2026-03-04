"""Lightness evaluation based on Kinetic Energy rarity."""

from dataclasses import dataclass
import numpy as np

from pyeyesweb.data_models.base import DynamicFeature
from pyeyesweb.data_models.results import FeatureResult
from pyeyesweb.low_level.kinetic_energy import KineticEnergy
from pyeyesweb.analysis_primitives.rarity import Rarity


@dataclass(slots=True)
class LightnessResult(FeatureResult):
    """Output contract for Lightness evaluation."""
    lightness: float = 0.0
    latest_weight_index: float = 0.0


class Lightness(DynamicFeature):
    """
    Computes Lightness by evaluating the rarity of the Vertical Kinetic Energy
    weight index over a time window.
    """

    def __init__(self, alpha: float = 0.5):
        super().__init__()
        self.alpha = alpha

        # Instantiate sub-features
        self._kinetic_energy = KineticEnergy()
        self._rarity = Rarity(alpha=self.alpha)

    def compute(self, window_data: np.ndarray, **kwargs) -> LightnessResult:
        """
        The Pure Math API.
        Expects window_data of shape (Time, N_signals, N_dims) representing VELOCITIES.
        """
        n_frames = window_data.shape[0]
        if n_frames < 2:
            return LightnessResult(is_valid=False)

        weight_indices = np.zeros(n_frames)

        # 1. Compute Kinetic Energy weight index for every frame in the window
        for i in range(n_frames):
            frame_vel = window_data[i]

            # KineticEnergy is a StaticFeature, so it expects a single frame (N_signals, N_dims)
            # We call the public compute method!
            ke_res = self._kinetic_energy.compute(frame_vel)

            if not ke_res.is_valid or ke_res.total_energy == 0:
                weight_indices[i] = 0.0
                continue

            # Vertical component is typically index 1 (Y) or 2 (Z) depending on coordinate system.
            # Assuming Y is vertical based on the original code `component_energy[1]`
            vertical_energy = ke_res.component_energy[1]
            weight_indices[i] = vertical_energy / (ke_res.total_energy + 1e-9)

        # Invert the weight index (as per original logic)
        inverted_weights = 1.0 - weight_indices

        # 2. Compute Rarity over the computed 1D weight index array
        # We call the public compute method!
        rarity_res = self._rarity.compute(inverted_weights)

        if not rarity_res.is_valid:
            return LightnessResult(is_valid=False)

        return LightnessResult(
            lightness=float(rarity_res.rarity),
            latest_weight_index=float(weight_indices[-1])
        )