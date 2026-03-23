# Geometric Symmetry Analysis Module

## Overview
The Geometric Symmetry module computes the instantaneous spatial symmetry error for a skeletal frame. It evaluates how closely a posture resembles perfect bilateral symmetry across a dividing anatomical plane.

## Theoretical Interpretation
- **Input Requirements**: Expects an instantaneous snapshot of joint positions (a single frame of shape `(N_signals, N_dims)`). Computes symmetry over user-specified paired joints (e.g., Left Hand and Right Hand).
- **Value Interpretation**: The result is a dictionary mapping each paired joint to a symmetry score bounded in `[0, 1]`. 
    - A score of `1.0` indicates perfect bilateral symmetry across the sagittal plane (assuming the X-axis represents lateral span).
    - Lower scores indicate asymmetry in posture.

!!! note "Center of Symmetry"
    Symmetry heavily depends on a reference origin. The module allows passing a explicit `center_of_symmetry` (like the spine or pelvis joint). By default, it will fall back to the overall barycenter of the given pose.

## Algorithm Details & Mathematics

For a given frame containing 3D (or 2D) positional input points, the algorithm centers the posture around the Center of Symmetry (CoS) $C$.

If $P$ is the matrix of all joints, the centered data $P'$ is:

$$
P' = P - C
$$

For every paired left ($L'$) and right ($R'$) joint, it reflects the right joint across the X-axis to test alignment with the left joint:

$$
R'_{reflected} = (-R'_x, R'_y, R'_z)
$$

The instantaneous Euclidean error $e$ is the distance between the left joint and the mathematically reflected right joint:

$$
e = \| L' - R'_{reflected} \|
$$

The symmetry score $S_{pair}$ returned for that specific interaction pair is:

$$
S_{pair} = 1.0 - e
$$

*(Note: If the input features are unscaled coordinates, large distances may yield negative values which are returned directly without clipping, serving as a relative displacement metric).*

## References

[^1]: Glowinski, D., Dael, N., Camurri, A., Volpe, G., Mortillaro, M., & Scherer, K. (2011). Toward a minimal representation of affective gestures. IEEE Transactions on Affective Computing, 2(2), 106-118
