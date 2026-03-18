# Impulsivity Analysis Module

## Overview
The Impulsivity module captures the burst-like, impulsive quality of a movement pattern. It conceptually pairs spatial abruptly-changing metrics with temporal suddenness metrics to define a singular 'Impulse'.

## Theoretical Interpretation
- **Input Requirements**: Expects a 3D tensor of positional motion data over time. It internally routes this data to sub-features.
- **Value Interpretation**: 
    - A high impulsivity index indicates a movement that is both **spatially sharp** (a sudden tight turn or change in geometric direction) and **temporally sudden** (a spike in velocity characteristic of a heavy-tailed distribution).
    - If the movement is entirely predictable or smooth (not sudden), impulsivity strictly evaluates to `0.0`.

## Algorithm Details & Mathematics
Impulsivity is fundamentally computed as the cross-product of spatial Direction Change (specifically its cosine similarity metric) and temporal Suddenness.

Let $D_{cos} \in [0, 1]$ be the cosine similarity score representing the sharpness of the trajectory's angle (derived from the `DirectionChange` module).
Let $S_{binary} \in \{0, 1\}$ be the boolean classification natively returned by the `Suddenness` module (where $1$ denotes a sudden movement phase, and $0$ denotes continuous).

The impulsive index $I$ is calculated as the simple scalar multiplier:

$$ 
I = D_{cos} \times S_{binary} 
$$

This ensures that high spatial curvature without temporal acceleration (e.g., slowly tracing a sharp corner) safely scores zero impulsivity.

## References

### TODO
