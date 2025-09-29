# Layer 2 – Low-Level Features

Low-level features are **instantaneous descriptors** of movement, usually computed directly from raw data (Layer 1) or from short sliding windows of samples.  
They are typically represented as **time-series** with the same sampling rate as the input signals.

## Examples of Low-Level Features

| Feature                                                   | Description                                                                                                                                                     | Implemented      |
|-----------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------|------------------|
| **Kinematics**                                            | Velocity, acceleration, and jerk.                                                                                                                               | :material-close: |
| **Gravity**                                               | Acceleration toward the ground.                                                                                                                                 | :material-close: |
| **Kinetic Energy**                                        | Energy of a cloud of 3D moving joints, possibly weighted by their masses using biometric tables.                                                                | :material-close: |
| **Motion Index / Quantity of Motion (QoM)**               | Area of the difference between silhouettes in consecutive frames.                                                                                               | :material-close: |
| [**Postural Contraction**](contraction_expansion.md) [^1] | Extent to which body posture is close to its barycenter.                                                                                                        | :material-close: |
| **Postural Symmetry**                                     | Geometric symmetry of posture with respect to a plane or axis.                                                                                                  | :material-close: |
| [**Smoothness**](smoothness.md) [^1]                      | Motion of a joint according to biomechanics laws of smoothness.                                                                                                 | :material-check: |
| [**Postural Balance**](postural_balance.md) [^1]          | Projection of the body’s barycenter onto the floor within the support area of the feet                                                                          | :material-check: |
| **Change of Weight Between Feet**                         | Computed from pressure patterns measured by a sensitive floor.                                                                                                  | :material-close: |
| **Postural Tension**                                      | Vector describing angular relations between feet, hips, trunk, shoulders, and head; inspired by angles in classical painting/sculpture used to express tension. | :material-close: |

---

## References
[^1]: TODO


