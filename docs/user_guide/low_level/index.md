# Layer 2 – Low-Level Features

Low-level features are **instantaneous descriptors** of movement, usually computed directly from raw data (Layer 1) or from short sliding windows of samples.  
They are typically represented as **time-series** with the same sampling rate as the input signals.

## Examples of Low-Level Features

| Feature                                                   | Description                                                                                                                                                     | Implemented      |
|-----------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------|------------------|
| **Kinematics** [^1]                                       | Velocity, acceleration, and jerk.                                                                                                                               | :material-close: |
| **Kinetic Energy** [^1]                                   | Energy of a cloud of 3D moving joints, possibly weighted by their masses using biometric tables.                                                                | :material-close: |
| **Motion Index / Quantity of Motion (QoM)** [^1]          | Area of the difference between silhouettes in consecutive frames.                                                                                               | :material-close: |
| [**Postural Contraction**](contraction_expansion.md) [^1] | Extent to which body posture is close to its barycenter.                                                                                                        | :material-close: |
| [**Smoothness**](smoothness.md) [^1]                      | Motion of a joint according to biomechanics laws of smoothness.                                                                                                 | :material-check: |
| [**Postural Balance**](postural_balance.md) [^1]          | Projection of the body’s barycenter onto the floor within the support area of the feet                                                                          | :material-check: |
| **Postural Tension** [^1]                                 | Vector describing angular relations between feet, hips, trunk, shoulders, and head; inspired by angles in classical painting/sculpture used to express tension. | :material-close: |

---

## References

[//]: # (Postural tension)
[^1]: Camurri, Volpe, Piana, Mancini, Alborno, Ghisio (2018) The Energy Lift: automated measurement of postural tension and energy transmission. Proc. MOCO 2018

[//]: # (Postural tension)
[^2]: Camurri, Volpe, Piana, Mancini, Niewiadomski, Ferrari, Canepa  (2016) The Dancer in the Eye: Towards a Multi-Layered Computational Framework of Qualities in Movement, Proc. MOCO 2016.


