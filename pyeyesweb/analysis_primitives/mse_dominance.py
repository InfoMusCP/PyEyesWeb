"""Multi-scale entropy analysis module for dominance detection in ensemble performances.

This module implements the multi-scale entropy (MSE) algorithm for analyzing
dominance and leadership in social creative activities. The method quantifies
the complexity of movement dynamics across multiple time scales to identify
leadership patterns in musical ensembles.

The multi-scale entropy algorithm includes:
1. Coarse-graining procedure for multi-scale signal representation
2. Sample entropy calculation for irregularity quantification
3. Complexity index computation across scales
4. Dominance analysis based on complexity differences

Typical use cases include:
1. Leadership detection in string quartet performances
2. Dominance analysis in social creative interactions
3. Group coordination pattern analysis
4. Movement complexity characterization
5. Real-time ensemble performance monitoring

References
----------
Glowinski, D., Coletta, P., Volpe, G., Camurri, A., Chiorri, C., & Schenone, A. (2010).
Multi-scale entropy analysis of dominance in social creative activities.
In Proceedings of the 18th ACM international conference on Multimedia (pp. 1035-1038).

Costa, M., Goldberger, A. L., & Peng, C.-K. (2005).
Multiscale entropy analysis of biological signals.
Physical Review E, 71(2), 021906.
"""

from typing import Literal
import numpy as np
from pyeyesweb.data_models.sliding_window import SlidingWindow
from pyeyesweb.utils.validators import validate_integer, validate_numeric, validate_string

class MultiScaleEntropyDominance:
    """Real-time multi-scale entropy analyzer for dominance detection.

    This class implements the multi-scale entropy algorithm to analyze dominance
    in ensemble performances by computing complexity indices of movement dynamics
    across multiple time scales.

    The algorithm follows the methodology described in:
    Glowinski et al. (2010). Multi-scale entropy analysis of dominance in
    social creative activities. ACM Multimedia, 1035-1038.
    """
    _ALLOWED_METHODS = ["complexity_index", "dominance_score", "leader_identification"]
    
    def __init__(self, 
                 m=2, 
                 r=0.15, 
                 max_scale=6, 
                 min_points=500, 
                 methods: list[Literal["complexity_index", "dominance_score", "leader_identification"]] = ["complexity_index"]):
        
        self._m = validate_integer(m, "m", min_val=1)                            # Embedding dimension for sample entropy
        self._r = validate_numeric(r, "r", min_val=0.0001, max_val=0.9999)       # Tolerance parameter (15% of standard deviation)
        self._max_scale = validate_integer(max_scale, "max_scale", min_val=1)            # Maximum scale factor for coarse-graining
        self._min_points = validate_integer(min_points, "min_points", min_val=1)          # Minimum data points required per scale
        self._methods = [validate_string(method, self._ALLOWED_METHODS) for method in methods]

    def _coarse_grain(self, data: np.ndarray, scale: int) -> np.ndarray:
        """Apply coarse-graining procedure to time series data.

        Implements the exact equation from Costa et al. (2005):
        y_j^(τ) = (1/τ) * Σ_{i=(j-1)τ+1}^{jτ} x_i, for j=1..floor(N/τ)

        Parameters
        ----------
        data : np.ndarray
            Input time series data (1D array)
        scale : int
            Scale factor for coarse-graining (τ in the equation)

        Returns
        -------
        np.ndarray
            Coarse-grained time series
        """
        if data is None or data.size == 0:
            return np.array([], dtype=float)

        x = np.asarray(data, dtype=float).ravel()

        if scale is None or scale < 1:
            return np.array([], dtype=float)

        if scale == 1:
            return x

        N = x.shape[0]
        if N < scale:
            return np.array([], dtype=float)

        # Calculate number of complete blocks
        num_points = N // scale

        # Trim data to complete blocks
        trimmed = x[:num_points * scale]

        # Reshape and average: each block becomes one point
        coarse = trimmed.reshape(num_points, scale).mean(axis=1)

        return coarse

    def _sample_entropy(self, data: np.ndarray) -> float:
        """Calculate sample entropy (SampEn) for a time series.

        Parameters
        ----------
        data : np.ndarray
            Input time series data (1D array)

        Returns
        -------
        float
            Sample entropy value, or nan if insufficient data
        """
        x = np.asarray(data, dtype=float).reshape(-1)
        N = x.shape[0]
        m = int(self._m)
        r = float(self._r)

        if N <= m + 10:
            return np.nan

        mu = float(np.mean(x))
        sd = float(np.std(x))
        if sd < 1e-10:
            return np.nan

        u = (x - mu) / sd

        templates_m = np.array([u[i:i + m] for i in range(N - m)], dtype=float)
        templates_m1 = np.array([u[i:i + m + 1] for i in range(N - m - 1)], dtype=float)

        n_m = templates_m.shape[0]
        n_m1 = templates_m1.shape[0]

        if n_m <= 1 or n_m1 <= 1:
            return 0.0

        B_matches = 0
        A_matches = 0

        for i in range(n_m):
            dist = np.max(np.abs(templates_m[i] - templates_m), axis=1)
            B_matches += int(np.sum(dist < r) - 1)

        for i in range(n_m1):
            dist = np.max(np.abs(templates_m1[i] - templates_m1), axis=1)
            A_matches += int(np.sum(dist < r) - 1)

        if B_matches <= 0 or A_matches <= 0:
            return 0.0

        B = B_matches / (n_m * (n_m - 1))
        A = A_matches / (n_m1 * (n_m1 - 1))

        if A <= 0 or B <= 0:
            return 0.0

        return float(-np.log(A / B))

    def _calculate_complexity_index(self, data: np.ndarray) -> float:
        """Calculate complexity index by integrating sample entropy across scales.

        Parameters
        ----------
        data : np.ndarray
            Input time series data

        Returns
        -------
        float
            Complexity index value
        """
        sampen_values = []

        for scale in range(1, int(self._max_scale) + 1):
            coarse = self._coarse_grain(data, scale)

            if coarse.shape[0] < int(self._min_points):
                break

            sampen = self._sample_entropy(coarse)
            sampen_values.append(sampen)

        if len(sampen_values) > 1:
            scales = np.arange(1, len(sampen_values) + 1, dtype=float)
            return float(np.trapz(np.asarray(sampen_values, dtype=float), x=scales))

        if len(sampen_values) == 1:
            return float(sampen_values[0])

        return 0.0

    def __call__(self, signals: SlidingWindow) -> dict:
        """Compute dominance analysis for ensemble performance data.

        Parameters
        ----------
        signals : SlidingWindow
            Sliding window buffer containing movement velocity data.

        Returns
        -------
        dict
            Dictionary containing dominance analysis results.
        """
        if not signals.is_full():
            return {method: np.nan for method in self._methods}

        data, _ = signals.to_array(as2D=True)
        n_samples, n_features = data.shape
        print(f"MultiScaleEntropyDominance: Processing {n_samples} samples with {n_features} features.")

        if n_samples < int(self._min_points):
            return {method: np.nan for method in self._methods}

        complexity_indices = []
        for i in range(n_features):
            ci = self._calculate_complexity_index(data[:, i])
            complexity_indices.append(ci)

        result = {}

        for method in self._methods:
            if method == 'complexity_index':
                values = np.array(complexity_indices, dtype=float)
                result['complexity_index'] = float(values[0]) if len(values) == 1 else values.tolist()

            elif method == 'dominance_score':
                cis = np.array(complexity_indices, dtype=float)
                if cis.size > 0:
                    max_ci = float(np.max(cis))
                    if max_ci > 0:
                        scores = (1.0 - (cis / max_ci))
                    else:
                        scores = np.zeros_like(cis)
                    result['dominance_score'] = float(scores[0]) if len(scores) == 1 else scores.tolist()

            elif method == 'leader_identification':
                if complexity_indices:
                    leader_idx = np.argmin(complexity_indices)
                    result['leader_complexity'] = (int(leader_idx),float(complexity_indices[leader_idx]))

        return result