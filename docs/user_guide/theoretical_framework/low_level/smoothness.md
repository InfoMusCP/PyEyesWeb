# Smoothness Analysis Module

## Overview
The Smoothness module quantifies control and fluidity of movement using established motor control metrics. Smooth movements are characterized by continuous, coordinated trajectories with minimal abrupt changes.

## Theoretical Interpretation
- **Input Requirements**: Expects a 1D scalar time-series over a temporal window. Crucially, the current implementation expects this sequence to represent a **speed profile** (magnitude of velocity).
- **Value Interpretation**:
    - **SPARC**: A frequency-domain measure where values are inherently negative. Values closer to `0.0` (less negative) denote smoother, more uniform movement. More negative values indicate jittery, erratic motion.
    - **Jerk RMS**: A time-domain measure where lower positive values indicate smoother motion. It penalizes sudden, high-magnitude accelerations/decelerations across the window.

!!! tip "Signal Filtering"
    Raw derived speed profiles are notoriously noisy. By default, the `Smoothness` module applies a Savitzky-Golay filter to clean the kinematic sequence prior to extracting SPARC or Jerk, avoiding noise amplification during differentiation.

## Algorithm Details & Mathematics

The module implements two primary metrics validated in motor control research.

### 1. Spectral Arc Length (SPARC)
The **Spectral Arc Length (SPARC)** quantifies movement smoothness by measuring the arc length of the **normalized Fourier magnitude spectrum** of the speed signal $s(t)$.

1. **Compute the Fourier magnitude spectrum**: Take the Fast Fourier Transform (FFT) of the input signal and keep only the positive frequencies:

$$
Y(f) = |\text{FFT}[s(t)]|_{f > 0}
$$

2. **Normalize the spectrum**: Normalize the magnitude by its maximum value:

$$
\hat{Y}(f) = \frac{Y(f)}{\max(Y(f))}
$$

3. **Calculate geometric arc length**: Compute the total Euclidean arc length of this curve across frequencies:

$$
L = \sum_{i=1}^{N-1} \sqrt{(f_{i+1} - f_i)^2 + (\hat{Y}_{i+1} - \hat{Y}_i)^2}
$$

4. **Return SPARC**:

$$
\text{SPARC} = -L
$$

### 2. Jerk Root Mean Square (RMS)
The **Jerk Root Mean Square (RMS)** measures smoothness as the average magnitude of the finite-difference derivative of the input signal. Because the input $s(t)$ is a speed profile, its first derivative represents acceleration, and the algorithmic logic correctly surfaces Jerk.

1. **Discrete Derivative**: Approximate the temporal derivative using finite differences with sampling rate $f_s$:

$$
j_i = \frac{s_{i+1} - s_i}{1 / f_s}
$$

2. **Root Mean Square**:

$$
\text{RMS}_j = \sqrt{\frac{1}{N} \sum_{i=1}^{N} j_i^2}
$$

## References

[^1]: Mazzarino, B., & Mancini, M. (2009). The need for impulsivity & smoothness: improving hci by qualitatively measuring new high-level human motion features. In Proceedings of the International Conference on Signal Processing and Multimedia Applications (IEEE sponsored).
[^2]: Melendez-Calderon, A., Shirota, C., & Balasubramanian, S. (2021). Estimating movement smoothness from inertial measurement units. Frontiers in bioengineering and biotechnology, 8, 558771.