# Clusterability Analysis Module

## Overview
The Clusterability module assesses the presence of meaningful non-random structure within a dataset. Specifically, it evaluates whether the multidimensional points in a sliding window exhibit clustering tendencies or are merely uniformly distributed noise.

## Theoretical Interpretation
- **Input Requirements**: Expects a 3D tensor of motion data over a window.
- **Value Interpretation**: The module computes the Hopkins Statistic ($H$).
    - $H \approx 1.0$: Indicates highly clustered data (the true data points are significantly closer to each other than uniformly generated random points are). This implies highly structured, repeating, or localized postures.
    - $H \approx 0.5$: Indicates a completely random, uniform distribution in space (no discernible structure).
    - $H \approx 0.0$: Indicates regularly spaced data (e.g., a perfect grid), which is rare in human movement.

## Algorithm Details & Mathematics
The feature employs the **Hopkins Statistic** based on Nearest Neighbor (NN) distances.

Given a dataset $X$ of size $N$, the algorithm:

1. Randomly selects a subset of $m$ real data points (where $m = N \times \text{subset\fraction}$).
2. Generates $m$ uniformly distributed simulated artificial points within the spatial bounding box of $X$.
3. For each real point $x_i$, it computes the distance $w_i$ to its nearest real neighbor in $X$.
4. For each artificial point $y_i$, it computes the distance $u_i$ to its nearest real neighbor in $X$.

The Hopkins statistic ($H$) is calculated as the relative magnitude of the artificial nearest neighbor distances versus the total distances:

$$ 
H = \frac{\sum_{i=1}^{m} u_i}{\sum_{i=1}^{m} u_i + \sum_{i=1}^{m} w_i} 
$$

*(Note: In some literature the numerator is $w_i$. The Python implementation uses $u_i$ in the numerator to ensure that highly clustered data (where real points are dense resulting in small $w_i$, but random points fall in empty space resulting in large $u_i$) approaches $1.0$.)*

## References
*Lawson, R.G. and Jurs, P.C., 1990. New index for clustering tendency and its application to chemical problems. Journal of Chemical Information and Computer Sciences, 30(1), pp.36-41.*
