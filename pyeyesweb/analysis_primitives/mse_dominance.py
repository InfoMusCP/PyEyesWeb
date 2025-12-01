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
"""

import numpy as np
from pyeyesweb.data_models.sliding_window import SlidingWindow


class MultiScaleEntropyDominance:
    """Real-time multi-scale entropy analyzer for dominance detection.

    This class implements the multi-scale entropy algorithm to analyze dominance
    in ensemble performances by computing complexity indices of movement dynamics
    across multiple time scales.

    The algorithm follows the methodology described in:
    Glowinski et al. (2010). Multi-scale entropy analysis of dominance in
    social creative activities. ACM Multimedia, 1035-1038.
    """

    def __init__(self):
        """Initialize the multi-scale entropy analyzer with default parameters."""
        # Algorithm parameters as per reference paper
        self.m = 2          # Embedding dimension for sample entropy
        self.r = 0.15       # Tolerance parameter (15% of standard deviation)
        self.max_scale = 6  # Maximum scale factor for coarse-graining
        self.min_points = 500  # Minimum data points required per scale

    def _coarse_grain(self, data: np.ndarray, scale: int) -> np.ndarray:
        """Apply coarse-graining procedure to time series data.

        Parameters
        ----------
        data : np.ndarray
            Input time series data
        scale : int
            Scale factor for coarse-graining

        Returns
        -------
        np.ndarray
            Coarse-grained time series
        """
        if scale == 1:
            return data

        n = len(data)
        if n < scale:
            return np.array([])

        # Number of coarse-grained points
        num_points = n // scale
        coarse = np.zeros(num_points)

        # Average non-overlapping windows
        for i in range(num_points):
            start_idx = i * scale
            end_idx = start_idx + scale
            coarse[i] = np.mean(data[start_idx:end_idx])

        return coarse

    def _sample_entropy(self, data: np.ndarray) -> float:
        """Calculate sample entropy (SampEn) for a time series.

        Implements Eq. 1 from the reference paper:
        n_i^m = (1/(N-m-1)) * Σ_{j=1,j≠i}^{N-m} Θ(r - ||u_i(m) - u_j(m)||_∞)

        Parameters
        ----------
        data : np.ndarray
            Input time series data

        Returns
        -------
        float
            Sample entropy value
        """
        N = len(data)
        m = self.m
        r = self.r

        if N <= m + 10:  # Need enough points for reliable estimation
            return 0.0

        # Standardize the data
        data_mean = np.mean(data)
        data_std = np.std(data)
        if data_std < 1e-10:
            return 0.0

        u = (data - data_mean) / data_std

        # Create template vectors of length m and m+1
        templates_m = np.array([u[i:i+m] for i in range(N-m)])
        templates_m1 = np.array([u[i:i+m+1] for i in range(N-m-1)])

        # Count similar templates using maximum norm
        B_matches = 0
        A_matches = 0

        n_templates_m = len(templates_m)
        n_templates_m1 = len(templates_m1)

        # Calculate matches for templates of length m
        for i in range(n_templates_m):
            # Vectorized distance calculation
            distances = np.max(np.abs(templates_m[i] - templates_m), axis=1)
            matches = np.sum(distances < r) - 1  # subtract self-comparison
            B_matches += matches

        # Calculate matches for templates of length m+1
        for i in range(n_templates_m1):
            # Vectorized distance calculation
            distances = np.max(np.abs(templates_m1[i] - templates_m1), axis=1)
            matches = np.sum(distances < r) - 1  # subtract self-comparison
            A_matches += matches

        # Avoid division by zero
        if n_templates_m <= 1 or n_templates_m1 <= 1 or B_matches == 0 or A_matches == 0:
            return 0.0

        # Calculate probabilities
        B = B_matches / (n_templates_m * (n_templates_m - 1))
        A = A_matches / (n_templates_m1 * (n_templates_m1 - 1))

        if A == 0 or B == 0:
            return 0.0

        # Sample entropy = -ln(A/B)
        return -np.log(A / B)

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

        for scale in range(1, self.max_scale + 1):
            # Apply coarse-graining
            coarse_data = self._coarse_grain(data, scale)

            # Check if we have enough points
            if len(coarse_data) < self.min_points:
                break

            # Calculate sample entropy at this scale
            sampen = self._sample_entropy(coarse_data)
            sampen_values.append(sampen)

        # Calculate complexity index by integration (trapezoidal rule)
        if len(sampen_values) > 1:
            scales = list(range(1, len(sampen_values) + 1))
            complexity_index = np.trapz(sampen_values, scales)
        elif len(sampen_values) == 1:
            complexity_index = sampen_values[0]
        else:
            complexity_index = 0.0

        return complexity_index

    def compute_dominance_analysis(self, signals: SlidingWindow, methods: list) -> dict:
        """Compute dominance analysis for ensemble performance data.

        Parameters
        ----------
        signals : SlidingWindow
            Sliding window buffer containing movement velocity data for musicians
        methods : list of str
            List of analysis methods to compute. Available options:
            'complexity_index', 'dominance_score', 'leader_identification'

        Returns
        -------
        dict
            Dictionary containing dominance analysis results, or empty dict if insufficient data
        """
        # Check if window is full
        if not signals.is_full():
            return {}

        data, _ = signals.to_array()
        n_samples, n_features = data.shape

        # Check if we have enough data
        if n_samples < self.min_points:
            return {}

        result = {}

        # Calculate complexity indices for each feature (musician)
        complexity_indices = []
        for i in range(n_features):
            ci = self._calculate_complexity_index(data[:, i])
            complexity_indices.append(ci)

        # Compute only the requested methods
        for method in methods:
            if method == 'complexity_index':
                values = np.array(complexity_indices)
                result['complexity_index'] = float(values[0]) if len(values) == 1 else values.tolist()

            elif method == 'dominance_score':
                # Lower complexity = higher dominance (as per paper hypothesis)
                if complexity_indices and max(complexity_indices) > 0:
                    scores = []
                    for ci in complexity_indices:
                        # Normalize and invert (lower complexity = higher score)
                        score = 1.0 - (ci / max(complexity_indices))
                        scores.append(score)

                    values = np.array(scores)
                    result['dominance_score'] = float(values[0]) if len(values) == 1 else values.tolist()
                else:
                    values = np.zeros_like(complexity_indices)
                    result['dominance_score'] = float(values[0]) if len(values) == 1 else values.tolist()

            elif method == 'leader_identification':
                # Identify leader as musician with lowest complexity index
                if complexity_indices:
                    leader_idx = np.argmin(complexity_indices)
                    result['leader'] = int(leader_idx)
                    result['leader_complexity'] = float(complexity_indices[leader_idx])

            else:
                # Skip invalid methods silently
                continue

        return result

    def __call__(self, sliding_window: SlidingWindow, methods: list) -> dict:
        """Compute dominance analysis metrics.

        Parameters
        ----------
        sliding_window : SlidingWindow
            Buffer containing multivariate data to analyze.
        methods : list of str
            List of analysis methods to compute.

        Returns
        -------
        dict
            Dictionary containing dominance analysis metrics.
        """
        return self.compute_dominance_analysis(sliding_window, methods)