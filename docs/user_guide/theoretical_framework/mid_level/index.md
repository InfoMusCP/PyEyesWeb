# Layer 3 – Mid-Level Features

Mid-level features capture **structural properties of movement** across units or time windows.  
They operate at a higher abstraction than low-level descriptors, often integrating multiple signals into **amodal features**.

!!! note "Key Concepts"
    - **Segmentation**: movements are divided into units that depends on the context (e.g., technical gestures in sport, choreographic phrases) or analyzed over defined windows (e.g., 0.5s - 3s).
    - **Amodal descriptors**: features meaningful across modalities (e.g., movement and audio).
    - **Trajectories in feature space**: sequences of values describing movement dynamics in multidimensional spaces.

## Examples of Mid-Level Features

| Feature                          | Description                                                              | Implemented      |
|----------------------------------|--------------------------------------------------------------------------|------------------|
| **Contraction / Expansion** [^1] | Movement contracting or expanding over time.                             | :material-close: |
| **Directness** [^1]              | Straight vs. flexible trajectory toward a target (Laban’s Space).        | :material-close: |
| **Lightness** [^1]               | Influence of gravity on movement (vertical vs. horizontal acceleration). | :material-close: |
| **Suddenness** [^1]              | Rapid vs. sustained velocity changes (Laban’s Time).                     | :material-close: |
| **Impulsivity** [^1]             | Abrupt movement without preparation by antagonist muscles.               | :material-close: |
| **Equilibrium** [^1]             | Stability or tendency to fall.                                           | :material-close: |
| **Fluidity** [^1]                | Smooth, wave-like propagation of movement across joints.                 | :material-close: |
| **Repetitiveness** [^1]          | Recurrence of similar movement patterns.                                 | :material-close: |
| **Tension** [^1]                 | Multi-plane rotations and spirals, derived from postural tension.        | :material-close: |
| **Origin** [^1]                  | Leading joint in a movement; leadership dynamics in groups.              | :material-close: |
| **Attraction** [^1]              | Influence of external points in space (magnet-like).                     | :material-close: |
| **Slowness** [^1]                | Sustained extremely slow motion.                                         | :material-close: |
| **Stillness** [^1]               | Minimal micro-movements (respiration, attention, emotion-driven).        | :material-close: |
| **Fragility** [^1]               | Vulnerability and delicacy in movement.                                  | :material-close: |

---

## References

[//]: # (Fluidity)
[^1]: Piana, S., Alborno, P., Niewiadomski, R., Mancini, M., Volpe, G., & Camurri, A. (2016, May). Movement fluidity analysis based on performance and perception. In Proceedings of the 2016 CHI conference extended abstracts on human factors in computing systems (pp. 1629-1636).
[//]: # (Fluidity)
[^2]: Alborno, P., Cera, A., Piana, S., Mancini, M., Niewiadomski, R., Canepa, C., Volpe G. & Camurri, A. (2016). Interactive sonification of movement qualities–a case study on fluidity. Proceedings of ISon, 35.

[//]: # (Fragility e Lightness)
[^3]: Niewiadomski, R., Mancini, M., Piana, S., Alborno, P., Volpe, G., & Camurri, A. (2017, November). Low-intrusive recognition of expressive movement qualities. In Proceedings of the 19th ACM international conference on multimodal interaction (pp. 230-237).)
[//]: # (Fragility e Lightness)
[^4]: Niewiadomski, R., Mancini, M., Cera, A., Piana, S., Canepa, C., & Camurri, A. (2019). Does embodied training improve the recognition of mid-level expressive movement qualities sonification?. Journal on Multimodal User Interfaces, 13, 191-203.

[//]: # (Impulsivity)
[^5]: Mazzarino, B., & Mancini, M. (2009). The need for impulsivity & smoothness: improving hci by qualitatively measuring new high-level human motion features. In Proceedings of the International Conference on Signal Processing and Multimedia Applications.
[//]: # (Impulsivity)
[^6]: Niewiadomski, R., Mancini, M., Volpe, G., & Camurri, A. (2015, September). Automated detection of impulsive movements in HCI. In Proceedings of the 11th Biannual Conference of the Italian SIGCHI Chapter (pp. 166-169).