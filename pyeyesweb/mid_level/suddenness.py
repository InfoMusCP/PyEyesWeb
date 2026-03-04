"""Suddenness evaluation based on velocity distribution."""

from dataclasses import dataclass
import numpy as np

from pyeyesweb.data_models.base import DynamicFeature
from pyeyesweb.data_models.results import FeatureResult


@dataclass(slots=True)
class SuddennessResult(FeatureResult):
    """Output contract for Suddenness evaluation."""
    is_sudden: bool = False
    alpha: float = 0.0
    beta: float = 0.0
    gamma: float = 0.0


class Suddenness(DynamicFeature):
    """
    Suddenness evaluation based on velocity distribution.
    ...
    (Docstrings omitted for brevity, keep yours!)
    """

    # Stable distribution fitting tables (McCulloch, 1986)
    _alpha_tab = np.array([
        [2, 1.916, 1.808, 1.729, 1.664, 1.563, 1.484, 1.391, 1.279, 1.128, 1.029, 0.896, 0.818, 0.698, 0.593],
        [2, 1.924, 1.813, 1.73, 1.663, 1.56, 1.48, 1.386, 1.273, 1.121, 1.021, 0.892, 0.812, 0.695, 0.59],
        [2, 1.924, 1.829, 1.737, 1.663, 1.553, 1.471, 1.378, 1.266, 1.114, 1.014, 0.887, 0.806, 0.692, 0.588],
        [2, 1.924, 1.829, 1.745, 1.668, 1.548, 1.46, 1.364, 1.25, 1.101, 1.004, 0.883, 0.801, 0.689, 0.586],
        [2, 1.924, 1.829, 1.745, 1.676, 1.547, 1.448, 1.337, 1.21, 1.067, 0.974, 0.855, 0.78, 0.676, 0.579],
        [2, 1.924, 1.829, 1.745, 1.676, 1.547, 1.438, 1.318, 1.184, 1.027, 0.935, 0.823, 0.756, 0.656, 0.563],
        [2, 1.924, 1.829, 1.745, 1.676, 1.547, 1.438, 1.318, 1.15, 0.973, 0.874, 0.769, 0.691, 0.595, 0.513]
    ])

    _beta_tab = np.array([
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        [2.16, 1.592, 0.759, 0.482, 0.36, 0.253, 0.203, 0.165, 0.136, 0.109, 0.096, 0.082, 0.074, 0.064, 0.056],
        [1, 3.39, 1.8, 1.048, 0.76, 0.518, 0.41, 0.332, 0.271, 0.216, 0.19, 0.163, 0.147, 0.128, 0.112],
        [1, 1, 1, 1.694, 1.232, 0.823, 0.632, 0.499, 0.404, 0.323, 0.284, 0.243, 0.22, 0.191, 0.167],
        [1, 1, 1, 1, 2.229, 1.575, 1.244, 0.943, 0.689, 0.539, 0.472, 0.412, 0.377, 0.33, 0.285],
        [1, 1, 1, 1, 1, 1, 1.906, 1.56, 1.23, 0.827, 0.693, 0.601, 0.546, 0.478, 0.428],
        [1, 1, 1, 1, 1, 1, 1, 1, 2.195, 1.917, 1.759, 1.596, 1.482, 1.362, 1.274]
    ])

    _a_vals = np.array([2.439, 2.5, 2.6, 2.7, 2.8, 3, 3.2, 3.5, 4, 5, 6, 8, 10, 15, 25])
    _b_vals = np.array([0.0, 0.1, 0.2, 0.3, 0.5, 0.7, 1.0])

    def __init__(self, algo: str = "new"):
        super().__init__()
        self.algo = algo

    def compute(self, window_data: np.ndarray, **kwargs) -> SuddennessResult:
        """
        The Pure Math API.
        Expects window_data shape (Time, N_signals, N_dims).
        """
        # Collapse signals and dims for velocity calculation
        # Assuming we track a single joint's trajectory for suddenness
        pos = window_data[:, 0, :]

        n_samples = pos.shape[0]
        if n_samples < 2:
            return SuddennessResult(is_valid=False)

        # Calculate velocities (magnitude of difference)
        diffs = pos[1:] - pos[:-1]
        velocities = np.linalg.norm(diffs, axis=1)

        if len(velocities) < 5:
            return SuddennessResult(is_valid=False)

        if self.algo == "new":
            alpha, beta, gamma, _ = self._fit_stable_constrained_bounds(velocities)
        else:
            alpha, beta, gamma, _ = self._fit_stable(velocities)

        is_sudden = gamma * (1.0 - (alpha / 2.0)) * beta >= 0.0  # TODO: is checking >= 0.0 correct?

        return SuddennessResult(
            is_sudden=bool(is_sudden),
            alpha=float(alpha),
            beta=float(beta),
            gamma=float(gamma)
        )

    def _interp2d(self, tab, nu_alpha, nu_beta):
        rows, cols = tab.shape
        a = self._a_vals
        b = self._b_vals

        row, col = -1, -1

        # Find the column index
        for i in range(1, cols):
            if a[i - 1] <= nu_alpha <= a[i]:
                col = i - 1
                break

        # Find the row index
        for i in range(1, rows):
            if b[i - 1] <= nu_beta <= b[i]:
                row = i - 1
                break

        if row != -1 and col != -1:
            relcol = abs(a[col] - nu_alpha) / abs(a[col] - a[col + 1])
            mean1 = tab[row, col] + (tab[row, col + 1] - tab[row, col]) * relcol
            mean2 = tab[row + 1, col] + (tab[row + 1, col + 1] - tab[row + 1, col]) * relcol

            relrow = abs(b[row] - nu_beta) / abs(b[row] - b[row + 1])
            result = mean1 + (mean2 - mean1) * relrow
            return result

        return -1.0

    def _fit_stable_constrained_bounds(self, data):
        # 1. Handle edge cases (empty data or constant values)
        if len(data) < 5 or np.all(data == data[0]):
            return 2.0, 0.0, 0.0, 0.0  # Return Gaussian (Normal) defaults

        # 2. Compute percentiles
        percentiles = [95, 75, 50, 25, 5]
        # using 'midpoint' interpolation is safer for small windows than default 'linear'
        x_percentiles = np.percentile(np.sort(data), percentiles, method='midpoint')

        x95, x75, x50, x25, x5 = x_percentiles

        # 3. Check for Zero Division (Interquartile range is 0)
        if (x75 - x25) == 0 or (x95 - x5) == 0:
            return 2.0, 0.0, 0.0, 0.0  # Fallback to Gaussian

        # 4. Calculate Quantile Measures
        nuAlpha = (x95 - x5) / (x75 - x25)
        nuBeta = (x95 + x5 - 2 * x50) / (x95 - x5)

        # 5. CRITICAL FIX: Clamp values to the lookup table bounds!
        # If nuAlpha < 2.439, it's Gaussian (Alpha=2). If > 25, it's Cauchy or worse.
        nuAlpha_clamped = np.clip(nuAlpha, self._a_vals[0], self._a_vals[-1])

        # nuBeta is theoretically between -1 and 1, but your table _b goes 0.0 to 1.0
        nuBeta_clamped = np.clip(abs(nuBeta), self._b_vals[0], self._b_vals[-1])

        # 6. Interpolate
        s = 1 if nuBeta >= 0. else -1
        alpha = self._interp2d(self._alpha_tab, nuAlpha_clamped, nuBeta_clamped)
        beta = s * self._interp2d(self._beta_tab, nuAlpha_clamped, nuBeta_clamped)

        # 7. Calculate Gamma and Delta
        denom_gamma = (x75 - x50)
        if denom_gamma == 0:
            gamma = 1.0
        else:
            gamma = (x75 - x25) / denom_gamma

        delta = x50 - beta * gamma * np.tan(np.pi * alpha / 2)  # Using x50 (median) is safer than x25

        return alpha, beta, gamma, delta

    def _fit_stable(self, data):
        """Fit data to stable distribution using quantile method."""
        # Compute percentiles
        percentiles = [95, 75, 50, 25, 5]
        x_pcts = np.percentile(data, percentiles)

        # Check for zero denominators
        range_95_5 = x_pcts[0] - x_pcts[4]
        range_75_25 = x_pcts[1] - x_pcts[3]
        range_75_50 = x_pcts[1] - x_pcts[2]

        if range_95_5 == 0 or range_75_25 == 0 or range_75_50 == 0:
            return 0.0, 0.0, 0.0, 0.0

        # Compute nuAlpha
        nu_alpha = range_95_5 / range_75_25

        # Compute nuBeta
        nu_beta = (x_pcts[0] + x_pcts[4] - 2 * x_pcts[2]) / range_95_5

        abs_nu_beta = abs(nu_beta)

        alpha = self._interp2d(self._alpha_tab, nu_alpha, abs_nu_beta)

        beta = max(min(nu_beta, 1.0), -1.0)

        gamma = range_75_25 / (x_pcts[1] - x_pcts[2])

        return alpha, beta, gamma, np.nan  # delta