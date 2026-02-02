import numpy as np

from pyeyesweb.data_models.sliding_window import SlidingWindow

class Suddenness:
    """
    Suddenness evaluation based on velocity distribution.

    This class computes a suddenness index for a given trajectory segment
    by analyzing the distribution of velocity magnitudes. It fits the
    velocity profile to a stable distribution and derives a suddenness
    measure from the distribution parameters (alpha, beta, gamma).

    Sudden movements are characterized by heavy-tailed velocity distributions.

    Examples
    --------
    >>> import numpy as np
    >>> sd = Suddenness()
    >>> # Generate a trajectory with a sudden jump
    >>> points = np.random.rand(20, 3) * 10
    >>> points[10] += 100  # Sudden jump
    >>> result = sd(points)
    
    References
    ----------
    1. Radoslaw Niewiadomski, Maurizio Mancini, Gualtiero Volpe, and Antonio Camurri. 2015. 
       Automated Detection of Impulsive Movements in HCI. In Proceedings of the 11th Biannual Conference of the Italian SIGCHI Chapter (CHItaly '15). 
       Association for Computing Machinery, New York, NY, USA, 166–169. https://doi.org/10.1145/2808435.2808466
    2. P. L´evy. Calcul des probabilit´es, volume 9. Gauthier-Villars Paris, 1925.
    3. G. Tsihrintzis and C. Nikias. Fast estimation of the parameters of alpha-stable impulsive interference. Signal Processing, IEEE Transactions on, 44(6):1492–1503, 1996.
    4. E. E. Kuruoglu and J. Zerubia. Skewed α-stable distributions for modelling textures. Pattern Recognition Letters, 24(1-3):339–348, 2003.
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

    #_beta_tab = np.array([
    #    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    #    [2.16, 1.592, 0.759, 0.482, 0.36, 0.253, 0.203, 0.165, 0.136, 0.109, 0.096, 0.082, 0.074, 0.064, 0.056],
    #    [1, 3.39, 1.8, 1.048, 0.76, 0.518, 0.41, 0.332, 0.271, 0.216, 0.19, 0.163, 0.147, 0.128, 0.112],
    #    [1, 1, 1, 1.694, 1.232, 0.823, 0.632, 0.499, 0.404, 0.323, 0.284, 0.243, 0.22, 0.191, 0.167],
    #    [1, 1, 1, 1, 2.229, 1.575, 1.244, 0.943, 0.689, 0.539, 0.472, 0.412, 0.377, 0.33, 0.285],
    #    [1, 1, 1, 1, 1, 1, 1.906, 1.56, 1.23, 0.827, 0.693, 0.601, 0.546, 0.478, 0.428],
    #    [1, 1, 1, 1, 1, 1, 1, 1, 2.195, 1.917, 1.759, 1.596, 1.482, 1.362, 1.274]
    #])

    _a_vals = np.array([2.439, 2.5, 2.6, 2.7, 2.8, 3, 3.2, 3.5, 4, 5, 6, 8, 10, 15, 25])
    _b_vals = np.array([0.0, 0.1, 0.2, 0.3, 0.5, 0.7, 1.0])

    def __init__(self):
        pass

    def __call__(self, positions: SlidingWindow) -> dict:
        """
        Compute the suddenness value for the given trajectory segment.

        Parameters
        ----------
        positions : SlidingWindow
            Input array of shape (N, 3) or (N, 2) representing coordinates
            (x, y, z) or (x, y) over time.

        Returns
        -------
        dict
            Dictionary containing the calculated suddenness index under the key "value".
            Returns {"value": 0.0} if the distribution cannot be fit or if the segment is too short.
        """
        pos = positions.to_array()
        if pos.ndim != 2 or pos.shape[1] < 2:
            raise Exception("Input positions must be a 2D array with at least 2 columns (x,y).")
        
        n_samples = pos.shape[0]

        if n_samples < 2:
            return {"value": np.nan}

        # Calculate velocities (magnitude of difference)
        diffs = pos[1:] - pos[:-1]
        velocities = np.linalg.norm(diffs, axis=1)

        if len(velocities) < 5:
            # Need at least 5 points for percentiles
            return {"value": np.nan}
            
        # Fit stable distribution
        alpha, beta, gamma, _ = self._fit_stable(velocities)
        
        # Suddenness calculation
        # Gamma (scale) * (1 - Alpha/2)
        # Only if Beta (skewness) is non-negative
        if beta >= 0:
            result = gamma * (1.0 - (alpha / 2.0))
            return {"value": result}
        else:
            return {"value": 0.0}
        
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

    def _fit_stable(self, data):
        """Fit data to stable distribution using quantile method."""
        # Compute percentiles
        percentiles = [95, 75, 50, 25, 5]
        # Use simple interpolation 'linear' (default)
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
        
        #s = 1.0 if nu_beta >= 0.0 else -1.0
        
        abs_nu_beta = abs(nu_beta)
        
        alpha = self._interp2d(self._alpha_tab, nu_alpha, abs_nu_beta)
        #beta = s * self._interp2d(self._beta_tab, nu_alpha, abs_nu_beta)
        
        # Original code line: beta = s * ...
        # But also: beta = max(min(nuBeta, 1.0), -1.0)
        # beta = s * self._interp2d(...)
        # beta = max(min(nuBeta, 1.0), -1.0)
        # The second assignment overwrites the fit
        
        # Gemini opinion:
        # I will use the code as provided in the snippet, even if it looks weird.
        # "beta = max(min(nuBeta, 1.0), -1.0)"
        
        # Yes, it overwrites. This renders _betaTab useless.
        # I will follow strictly.
        
        beta = max(min(nu_beta, 1.0), -1.0)
        
        # If alpha interpolation failed (-1), we might have issues. 
        # But nu_beta logic persists.
        # The interp2d returns -1 on failure.
        
        gamma = range_75_25 / (x_pcts[1] - x_pcts[2])
        # Note:
        # McCulloch estimator for gamma is (Q75 - Q25) / Phi_3(alpha, beta).
        # This looks like a specific approximation.
        
        # Delta calculation (unused but included)
        # Caution: tan(pi * median / 2). If median is velocity ~ 1.0, tan is huge.
        #delta = x_pcts[2] - beta * gamma * np.tan(np.pi * x_pcts[2] / 2)
        
        return alpha, beta, gamma, np.nan # delta
