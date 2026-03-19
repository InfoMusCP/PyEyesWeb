# Rarity Analysis Module

## Overview
The Rarity module quantifies the statistical novelty or anomaly of the most recent movement frame relative to the preceding history. It evaluates how unexpected a given value is by comparing it against a dynamically constructed probability distribution of the previous temporal window.

## Theoretical Interpretation
- **Input Requirements**: Expects a single 1D array representing a temporal sequence of aggregated scalar values (for instance, the output values of a specific sub-feature like Vertical Kinetic Energy weight or distance over time).
- **Value Interpretation**:
    - **High Rarity (approaching `1.0`)**: The latest movement is highly anomalous or unusual compared to the immediate past.
    - **Low Rarity (approaching `0.0`)**: The latest movement falls squarely within the most common, frequent, and expected behavior observed inside the target window.

## Algorithm Details & Mathematics
The Rarity $R$ is calculated using a convex combination of two distinct metrics derived from the probability density of the recent sequence window: 

1. The contextual Unlikelihood ($U$) of the final point.
2. The Normalized Shannon Entropy ($H_{norm}$) of the entire context window.

Given a sequence window $S$ of length $N$:

1. **Histogram Construction**:
The algorithm constructs a dynamic probability density function by segmenting the range `[min(S), max(S)]` into $B$ bins, where the optimal bin count dynamically scales with the available data:

$$ B = \max(\lfloor\sqrt{N}\rfloor, 1) $$

The probability $p_b$ of any bin $b$ is the frequency of points falling into that bin divided by $N$.

2. **Unlikelihood ($U$)**:
The unlikelihood algorithm isolates the raw probability of the specific bin containing the most recent observation ($p_{current}$). A very infrequent behavior has a low probability.

$$ U = 1.0 - p_{current} $$

3. **Normalized Entropy ($H_{norm}$)**:
Standard Shannon entropy evaluates the overall diversity or chaos of the window's distribution:

$$ H_{norm} = -\frac{1}{\log(B)} \sum_{b=1}^{B} p_b \log(p_b) $$

4. **Final Rarity Score**:
The rarity is returned as a weighted blend of the single-point unlikelihood and the holistic window unpredictability, governed by a configurable parameter $\alpha \in [0, 1]$:

$$ R = \alpha \cdot U + (1 - \alpha) \cdot H_{norm} $$

## References

[^1]: Niewiadomski, R., Mancini, M., Cera, A., Piana, S., Canepa, C., & Camurri, A. (2019). Does embodied training improve the recognition of mid-level expressive movement qualities sonification?. Journal on Multimodal User Interfaces, 13, 191-203.