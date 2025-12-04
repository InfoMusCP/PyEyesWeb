# Layer 3 – Mid-Level Features

Mid-level features capture **structural properties of movement** across units or time windows.  
They operate at a higher abstraction than low-level descriptors, often integrating multiple signals into **amodal features**.

!!! note "Key Concepts"
    - **Segmentation**: movements are divided into units that depends on the context (e.g., technical gestures in sport, choreographic phrases) or analyzed over defined windows (e.g., 0.5s - 3s).
    - **Amodal descriptors**: features meaningful across modalities (e.g., movement and audio).
    - **Trajectories in feature space**: sequences of values describing movement dynamics in multidimensional spaces.

## Examples of Mid-Level Features

| Feature                  | Description                                                              | Implemented      |
|--------------------------|--------------------------------------------------------------------------|------------------|
| **Directness** [^1]      | Straight vs. flexible trajectory toward a target (Laban’s Space).        | :material-close: |
| **Lightness** [^2][^3]   | Influence of gravity on movement (vertical vs. horizontal acceleration). | :material-close: |
| **Impulsivity** [^4][^5] | Abrupt movement without preparation by antagonist muscles.               | :material-close: |
| **Fluidity** [^6][^7]    | Smooth, wave-like propagation of movement across joints.                 | :material-close: |
| **Fragility** [^2][^3]   | Vulnerability and delicacy in movement.                                  | :material-close: |


## References

[^1]: Piana, S., Staglianò, A., Camurri, A., & Odone, F. (2013). A set of full-body movement features for emotion recognition to help children affected by autism spectrum condition. In IDGEI International Workshop (Vol. 23).
[^2]: Niewiadomski, R., Mancini, M., Piana, S., Alborno, P., Volpe, G., & Camurri, A. (2017). Low-intrusive recognition of expressive movement qualities. In Proceedings of the 19th ACM international conference on multimodal interaction (pp. 230-237).)
[^3]: Niewiadomski, R., Mancini, M., Cera, A., Piana, S., Canepa, C., & Camurri, A. (2019). Does embodied training improve the recognition of mid-level expressive movement qualities sonification?. Journal on Multimodal User Interfaces, 13, 191-203.
[^4]: Mazzarino, B., & Mancini, M. (2009). The need for impulsivity & smoothness: improving hci by qualitatively measuring new high-level human motion features. In Proceedings of the International Conference on Signal Processing and Multimedia Applications.
[^5]: Niewiadomski, R., Mancini, M., Volpe, G., & Camurri, A. (2015). Automated detection of impulsive movements in HCI. In Proceedings of the 11th Biannual Conference of the Italian SIGCHI Chapter (pp. 166-169).
[^6]: Piana, S., Alborno, P., Niewiadomski, R., Mancini, M., Volpe, G., & Camurri, A. (2016). Movement fluidity analysis based on performance and perception. In Proceedings of the 2016 CHI conference extended abstracts on human factors in computing systems (pp. 1629-1636).
[^7]: Alborno, P., Cera, A., Piana, S., Mancini, M., Niewiadomski, R., Canepa, C., Volpe G. & Camurri, A. (2016). Interactive sonification of movement qualities–a case study on fluidity. Proceedings of ISon, 35.
