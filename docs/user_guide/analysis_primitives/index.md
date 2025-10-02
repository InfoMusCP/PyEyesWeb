# Analysis Primitives

Analysis primitives are **operators applied across layers** to extract meaningful patterns from features.  
They summarize, transform, or model data at various temporal and spatial scales.

## Example of Analysis Primitives

| Primitive Type                | Description                                                                                                  | Implemented      |
|-------------------------------|--------------------------------------------------------------------------------------------------------------|------------------|
| **Statistical Moments**       | Unary operators summarizing distributions (mean, variance, skewness, kurtosis).                              | :material-close: |
| **Shape Descriptors**         | Peaks, slopes, valleys in time-series; geometric descriptors of movement curves.                             | :material-close: |
| **Entropy & Complexity**      | Approximate/sample entropy, recurrence analysis; quantify predictability or irregularity.                    | :material-close: |
| **Time-Frequency Transforms** | Fourier or wavelet transforms to detect rhythm, periodicity, or temporal structures.                         | :material-close: |
| **Symmetry** [^1]             | Unary/binary operators measuring geometric or dynamic balance (e.g., left vs. right entropy or energy).      | :material-close: |
| **Synchronization** [^2]      | Binary/n-ary operators measuring alignment of signals (cross-correlation, phase-locking, group entrainment). | :material-close: |
| **Causality**                 | Directional relationships (e.g., Granger causality, transfer entropy) to detect leader–follower dynamics.    | :material-close: |
| **Clusterability** [^3]       | Measures the tendency of data points to form clusters by means of the Hopkins statistics.                    | :material-close: |
| **Predictive Models**         | Hidden Markov Models, classifiers, neural networks; used for gesture segmentation or quality inference.      | :material-close: |
| **Physical Models**           | Biomechanical analogies (mass–spring–damper systems) to capture dynamics such as Fluidity.                   | :material-close: |
| **Saliency / Rarity** [^4]    | Detecting unusual occurrences in movement with respect to most frequent patterns.                            | :material-close: |


## References

[//]: # (Saliency )
[^4]: Niewiadomski, R., Mancini, M., Cera, A., Piana, S., Canepa, C., & Camurri, A. (2019). Does embodied training improve the recognition of mid-level expressive movement qualities sonification?. Journal on Multimodal User Interfaces, 13, 191-203.

[//]: # (Clusterability)
[^3]: Corbellini, N., Ceccaldi, E., Varni, G., & Volpe, G. (2022, August). An exploratory study on group potency classification from non-verbal social behaviours. In International Conference on Pattern Recognition (pp. 240-255). Cham: Springer Nature Switzerland.