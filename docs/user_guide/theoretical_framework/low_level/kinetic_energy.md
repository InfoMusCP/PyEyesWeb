# Kinetic Energy Analysis Module

## Overview
The Kinetic Energy module provides a real-time computation of weighted kinetic energy from joint velocities.

## Theoretical Interpretation
- **Input Requirements**: This feature inherently tracks movement magnitude derived from the speed of the body segments over time. Therefore, it **requires velocity inputs** rather than raw positions.
- **Value Interpretation**: 
    - Higher total kinetic energy corresponds to faster, more expansive, and high-effort movements involving heavily weighted joints.
    - The `weights` array allows the model to approximate true physical mass by treating the limbs with anatomically correct inertial weightings.

!!! tip "Velocity Derivation"
    If you only have raw positional data, you must apply a derivative operator such as `extract_velocity_from_position` before passing the data to this module.

## Algorithm Details & Mathematics

The kinetic energy $E_k$ of the full body is computed as the sum of translational kinetic energy over all constituent joints.

$$ 
E_k = \frac{1}{2} \cdot \sum_{i=1}^{N} w_i \cdot \|v_i\|^2 
$$

where:

- $w_i$ is the configured weight (mass multiplier) of the $i$-th joint.
- $N$ is the total number of joints.
- $v_i$ is the velocity vector of the $i$-th joint supplied in the input frame.

The `KineticEnergy` feature (a port of the EyesWeb *KineticEnergyIndex* block) returns a single output, `kinetic_energy`: the scalar sum $E_k$. It does not break the energy down by joint or by axis; to inspect one joint or one axis, compute the feature on that subset of the input.
## References

[^1]: Glowinski, D., Dael, N., Camurri, A., Volpe, G., Mortillaro, M., & Scherer, K. (2011). Toward a minimal representation of affective gestures. IEEE Transactions on Affective Computing, 2(2), 106-118.
[^2]: Camurri, A., Lagerlöf, I., & Volpe, G. (2003). Recognizing emotion from dance movement: comparison of spectator recognition and automated techniques. International journal of human-computer studies, 59(1-2), 213-225.