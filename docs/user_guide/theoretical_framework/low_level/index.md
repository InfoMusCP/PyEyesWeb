# Layer 2 – Low-Level Features

Low-level features are **instantaneous descriptors** of movement, usually computed directly from raw data (Layer 1) or from short sliding windows of samples.  
They are typically represented as **time-series** with the same sampling rate as the input signals.

## Examples of Low-Level Features

| Feature                                                       | Description                                                                                                                                                     | Implemented      |
|---------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------|------------------|
| **Kinectic Energy / Quantity of Motion** (QoM) [^1][^2]       | Energy of a cloud of moving joints, weighted by their masses or area of the difference between consecutive silhouettes in consecutive frames                    | :material-close: |
| [**Postural Contraction**](contraction_expansion.md) [^1][^2] | Extent to which body posture is close to its barycenter.                                                                                                        | :material-check: |
| [**Smoothness**](smoothness.md) [^3]                          | Motion of a joint according to biomechanics laws of smoothness.                                                                                                 | :material-check: |
| [**Equilibrium**](postural_balance.md) [^4]                   | Projection of the body’s barycenter onto the floor within the support area of the feet                                                                          | :material-check: |
| **Postural Tension** [^5]                                     | Vector describing angular relations between feet, hips, trunk, shoulders, and head; inspired by angles in classical painting/sculpture used to express tension. | :material-close: |


## References

[^1]: Glowinski, D., Dael, N., Camurri, A., Volpe, G., Mortillaro, M., & Scherer, K. (2011). Toward a minimal representation of affective gestures. IEEE Transactions on Affective Computing, 2(2), 106-118.
[^2]: Camurri, A., Lagerlöf, I., & Volpe, G. (2003). Recognizing emotion from dance movement: comparison of spectator recognition and automated techniques. International journal of human-computer studies, 59(1-2), 213-225.
[^3]: Mazzarino, B., & Mancini, M. (2009). The need for impulsivity & smoothness: improving hci by qualitatively measuring new high-level human motion features. In Proceedings of the International Conference on Signal Processing and Multimedia Applications (IEEE sponsored).
[^4]: Ghisio, S., Coletta, P., Piana, S., Alborno, P., Volpe, G., Camurri, A., ... & Ravaschio, A. (2015, June). An open platform for full body interactive sonification exergames. In 2015 7th International Conference on Intelligent Technologies for Interactive Entertainment (INTETAIN) (pp. 168-175). IEEE.
[^5]: Camurri, Volpe, Piana, Mancini, Alborno, Ghisio (2018) The Energy Lift: automated measurement of postural tension and energy transmission. Proc. MOCO 2018


