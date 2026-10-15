# Direction Change Analysis Module

## Overview
The Direction Change module evaluates the geometric trajectories of movement vectors over a temporal window. It offers metrics to identify sharp changes in movement direction (via cosine similarity) and to quantify the total spatial span enclosed by a movement trajectory (via polygon area).

## Theoretical Interpretation
- **Input Requirements**: The algorithms expect a complete trajectory over a time window. Input is averaged across all joints in the frame to construct a single global trajectory vector, requiring at least 2D `(x, y)` positional data.
- **Value Interpretation**:
    - **Cosine Metric**: A value close to `1.0` indicates a sharp angle change aligned exactly with the configured `epsilon` threshold. A value of `0.0` suggests either continuous smooth movement or a direction change outside the threshold of interest.
    - **Polygon Metric**: Captures the geometric area contained within the movement path boundaries. Large values indicate sweeping, broad movements enclosing significant space, while small values describe narrow or linear movements.

!!! tip "Metric Selection"
    You can selectively compute just the cosine similarity, just the polygon area, or both, depending on whether you are interested in sudden sharp turns or overall spatial usage.

## Algorithm Details & Mathematics

The module first aggregates the provided sequence of frames by taking the mean across all signal nodes to establish a single center-of-mass trajectory $P(t)$.

### 1. Cosine Similarity (Sharp Change Detection)
Evaluates the angle between the start, middle, and end segments of the trajectory.
Let the target trajectory consist of $N$ samples. The method extracts three key points:

- $P_0$ = `pos[-1]` (End point)
- $P_1$ = `pos[N//2]` (Mid point)
- $P_2$ = `pos[0]` (Start point)

It forms two directional vectors:

$$ L_0 = P_0 - P_1 $$ 

$$ L_1 = P_1 - P_2 $$

The angle $\theta$ between the vectors is calculated as:

$$
\theta = \arccos\left(\frac{L_0 \cdot L_1}{\|L_0\| \|L_1\|}\right)
$$

The angle is normalized to a $[0, 1]$ scale ($\theta_{norm} = \theta / \pi$). The final score is thresholded against an `epsilon` ($\epsilon$) parameter, looking for a target deviation $a = 1.0 - \theta_{norm}$.
The index $D_{cos}$ is given by:

$$
D_{cos} = 
\begin{cases} 
1.0 - \frac{|a - 0.5|}{\epsilon} & \text{if } |a - 0.5| < \epsilon \\
0.0 & \text{otherwise}
\end{cases}
$$

### 2. Polygon Area
Measures the geometric area enclosed by the path.
The continuous trajectory is first securely subsampled down to a specified `num_subsamples` to reduce noise. Let this closed polygon subset of points be $\{ X_i \}$.

The area is calculated using a generalized Shoelace-style cross product:

$$
Area = \left\| \frac{1}{2} \sum_{i} X_i \times X_{i+1} \right\|
$$

## References

### TODO