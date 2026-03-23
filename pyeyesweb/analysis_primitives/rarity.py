"""Rarity analysis based on histogram distribution.

This module implements the [Rarity][pyeyesweb.analysis_primitives.rarity.Rarity]
feature, which evaluates how typical or atypical the current movement state is
relative to the distribution of states within a sliding window.
"""

from dataclasses import dataclass
import numpy as np

from pyeyesweb.data_models.base import DynamicFeature
from pyeyesweb.data_models.results import FeatureResult
from pyeyesweb.utils.validators import validate_numeric


@dataclass(slots=True)
class RarityResult(FeatureResult):
    r"""Output contract for Rarity.
    
    Attributes
    ----------
    rarity : float
        Rarity score $\\ge 0$. Higher values indicate more atypical movement.
    """
    rarity: float = 0.0


class Rarity(DynamicFeature):
    r"""Compute rarity of the latest sample relative to the window distribution.

    Notes
    -----
    The number of histogram bins is set adaptively to
    $\max(\lfloor\sqrt{N}\rfloor, 1)$ where $N$ is the total number of samples,
    approximating the rule of thumb for histogram bin selection.

    !!! note
        Rarity is estimated by comparing the probability of the most recent sample
        against the most probable state in the current window's histogram.

    Read more in the [User Guide](../../user_guide/theoretical_framework/analysis_primitives/rarity.md).

    Parameters
    ----------
    alpha : float, optional
        Scaling factor for the rarity calculation. Defaults to `0.5`.

    Examples
    --------
    >>> rarity = Rarity(alpha=1.0)
    """

    def __init__(self, alpha: float = 0.5):
        super().__init__()
        self.alpha = alpha

    @property
    def alpha(self) -> float:
        """Scaling factor for rarity."""
        return self._alpha

    @alpha.setter
    def alpha(self, value: float):
        self._alpha = validate_numeric(value, "alpha")

    def compute(self, window_data: np.ndarray) -> RarityResult:
        r"""Compute rarity of the latest sample within the window distribution.

        Parameters
        ----------
        window_data : numpy.ndarray
            Window of motion data of any shape. The array is flattened to 1-D
            before building the histogram, so all values within the window
            contribute to the distribution estimate.

        Returns
        -------
        RarityResult
            Result containing the rarity score. Returns
            `RarityResult(is_valid=False)` when fewer than 2 samples are
            present in the window.
        """
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