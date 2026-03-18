# Multi-Scale Entropy Dominance Analysis Module

## Overview
The Multi-Scale Entropy (MSE) Dominance module implements a sophisticated non-linear analysis algorithm to detect leadership and dominance within ensemble performances based on movement complexity. 

## Theoretical Interpretation
- **Input Requirements**: Expects a lengthy sliding window of movement velocity data. Minimum sample threshold strongly applies (e.g., 500 samples) because entropy estimation is mathematically unstable on short sequences.
- **Value Interpretation**:
    - **Complexity Index (CI)**: Represents the overall irregularity and unpredictability of a signal across multiple temporal resolutions. A signal is "complex" if it retains structural unpredictability across scales (unlike white noise which loses structure when scaled, or simple sine waves which are entirely predictable).
    - **Dominance Score**: Computes the relative dominance within a multi-agent group. The actor with the *lowest* movement complexity (lowest CI) is typically classified as the leader, acting as a periodic anchor around which other participants exhibit higher, reactive complexity.
    - **Leader Identification**: A direct argmin pointer to the index of the predicted group leader.

## Algorithm Details & Mathematics
The algorithm leverages Multi-Scale Entropy, which consists of three sequential steps:

### 1. Coarse-Graining
The original signal $x = \{x_1, x_2, \dots, x_N\}$ is segmented into non-overlapping windows of length $\tau$ (the scale factor). The coarse-grained signal $y^{(\tau)}$ at scale $\tau$ is formed by averaging the data points within each window:
$$ 
y_j^{(\tau)} = \frac{1}{\tau} \sum_{i=(j-1)\tau + 1}^{j\tau} x_i 
$$
This is repeated for all scales from $\tau = 1$ to $\tau = max\_scale$.

### 2. Sample Entropy (SampEn)
For each coarse-grained signal, the Sample Entropy is computed. SampEn quantifies the conditional probability that two sequences that are similar for $m$ points remain similar at $m+1$ points, given a tolerance $r$.
$$ 
\text{SampEn}(m, r) = -\ln\left(\frac{A}{B}\right) 
$$
where $B$ is the number of template matches of length $m$, and $A$ is the number of strict template matches of length $m+1$.

### 3. Complexity Index (CI)
The final Complexity Index for an individual signal is the numerical integration (area under the curve) of the Sample Entropy values across all considered scales:
$$ 
CI = \int_{1}^{max\_scale} \text{SampEn}(\tau) \, d\tau 
$$

### 4. Dominance Mapping
In a multi-participant context, the dominant actor is identified. The dominance score scales the $CI$ relative to the group's maximum entropy:
$$ 
\text{Dominance} = 1.0 - \frac{CI_i}{\max(CI)} 
$$

## References
*Glowinski, D., Coletta, P., Volpe, G., Camurri, A., Chiorri, C., & Schenone, A. (2010). Multi-scale entropy analysis of dominance in social creative activities. In Proceedings of the 18th ACM international conference on Multimedia (pp. 1035-1038).*
