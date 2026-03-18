# Postural Balance (Equilibrium) Analysis Module

## Overview
The Postural Balance module provides a robust elliptical equilibrium evaluation metric. It computes how well a subject's barycenter is centered between two base-of-support points (e.g., the left and right feet) to mathematically estimate the stability of a physical posture.

## Theoretical Interpretation
- **Input Requirements**: Expects a single frame of static position data spanning multiple joints. The algorithm exclusively relies on a **2D projection** (specifically, the X and Y components) ignoring height (Z), as postural stability relative to the ground is a planar problem.
- **Value Interpretation**: 
    - An equilibrium value of `1.0` indicates perfect centering (the barycenter perfectly splits the base of support). 
    - Values approaching `0.0` indicate extreme stretching, leaning, or falling, where the user's center of mass is breaching the edge of their support ellipse. 
    - The algorithm also reports the `angle` of the base of support relative to the horizontal plane.

!!! note "Margin Safeties"
    The mathematical ellipse is intentionally inflated by a `margin_mm` config to account for the physical footprint size extending beyond the single theoretical "foot joint" point tracked by typical pose systems.

## Algorithm Details & Mathematics

The stable base of support is modeled as a 2D ellipse drawn around the left foot ($P_{left}$) and right foot ($P_{right}$). 

1. **Center and Axes Formulation**
The center point $C$ between the feet is derived as:

$$
C = \frac{P_{left} + P_{right}}{2}
$$

The Euclidean distance between the feet is $d = \|P_{right} - P_{left}\|$.
The ellipse semi-major axis ($a$) incorporates the safety margin:

$$
a = \frac{d}{2} + margin
$$

The ellipse semi-minor axis ($b$) determines the depth of the stability stance, weighted by $y\_weight$:

$$
b = margin \times y\_weight
$$

2. **Rotational Alignment**
The system computes the relative position of the barycenter to the geometric center $C$, and rotates this relative vector to align linearly with the vector bridging the two feet. Let this rotated barycenter coordinate be $B' = (x', y')$.

3. **Elliptical Evaluation**
The normalized distance equation inside the ellipse is computed as:

$$
norm = \left(\frac{x'}{a}\right)^2 + \left(\frac{y'}{b}\right)^2
$$

The final equilibrium score $Value \in [0, 1]$ is extracted inversely from the norm:

$$
Value = 
\begin{cases} 
1.0 - \sqrt{norm} & \text{if } norm \le 1.0 \\
0.0 & \text{otherwise}
\end{cases}
$$

## References

### TODO
