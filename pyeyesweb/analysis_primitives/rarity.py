from dataclasses import dataclass
import numpy as np

from pyeyesweb.data_models.base import DynamicFeature
from pyeyesweb.data_models.results import FeatureResult
from pyeyesweb.utils.validators import validate_numeric


@dataclass(slots=True)
class RarityResult(FeatureResult):
    """Output contract for Rarity."""
    rarity: float = 0.0


class Rarity(DynamicFeature):
    """Compute rarity of the latest sample relative to the window distribution."""

    def __init__(self, alpha: float = 0.5):
        super().__init__()
        self.alpha = alpha

    @property
    def alpha(self) -> float:
        return self._alpha

    @alpha.setter
    def alpha(self, value: float):
        self._alpha = validate_numeric(value, "alpha")

    def compute(self, window_data: np.ndarray) -> RarityResult:
        # Flatten to 1D array of samples
        samples = window_data.ravel()
        n_samples = len(samples)

        if n_samples < 2:
            return RarityResult(is_valid=False)

        # Number of bins
        n_bins = max(int(np.sqrt(n_samples)), 1)
        counts, bin_edges = np.histogram(samples, bins=n_bins)
        probabilities = counts / n_samples

        # Most probable bin vs Current sample bin
        most_probable_bin_index = np.argmax(probabilities)
        most_probable_p = probabilities[most_probable_bin_index]

        last_sample = samples[-1]
        last_sample_bin_index = np.searchsorted(bin_edges, last_sample, side='right') - 1
        last_sample_bin_index = np.clip(last_sample_bin_index, 0, n_bins - 1)
        last_sample_p = probabilities[last_sample_bin_index]

        d1 = abs(most_probable_bin_index - last_sample_bin_index)
        d2 = most_probable_p - last_sample_p

        rarity = d1 * d2 * self._alpha
        return RarityResult(rarity=float(rarity))