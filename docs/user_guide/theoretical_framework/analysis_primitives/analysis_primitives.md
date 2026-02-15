<style>
  /* 1. First Column: Allow wrapping and set modest width */
  .rst-content table.docutils td:nth-child(1) {
      width: 25%;              /* Fixed width for the feature name */
      white-space: normal !important; /* ALLOWS wrapping */
      word-wrap: break-word;   /* Breaks long words if necessary */
  }

  /* 2. Second Column: Maximize width */
  .rst-content table.docutils td:nth-child(2) {
      white-space: normal !important;
      word-wrap: break-word !important;
      width: 70%;              /* Takes up the majority of the table */
  }

  /* 3. Third Column: Keep it tight (Optional but recommended) */
  .rst-content table.docutils td:nth-child(3) {
      width: 10%;
      white-space: nowrap;
      text-align: center;
  }

  /* 4. Fix the Huge Icons */
  .rst-content .twemoji {
      height: 1.2em !important;
      width: 1.2em !important;
      vertical-align: text-bottom;
  }
</style>

# Analysis Primitives

Analysis primitives are **operators applied across layers** to extract meaningful patterns from features.  
They summarize, transform, or model data at various temporal and spatial scales.

## Example of Analysis Primitives

| Primitive Type                | Description                                                                                                  | Implemented      |
|-------------------------------|--------------------------------------------------------------------------------------------------------------|------------------|
| **Statistical Moments**       | Unary operators summarizing distributions (mean, variance, skewness, kurtosis).                              | :material-close: |
| **Shape Descriptors**         | Peaks, slopes, valleys in time-series; geometric descriptors of movement curves.                             | :material-close: |
| **Entropy** [^1]              | Approximate/sample entropy, recurrence analysis; quantify predictability or irregularity.                    | :material-close: |
| **Time-Frequency Transforms** | Fourier or wavelet transforms to detect rhythm, periodicity, or temporal structures.                         | :material-close: |
| **Symmetry** [^2]             | Unary/binary operators measuring geometric or dynamic balance (e.g., left vs. right entropy or energy).      | :material-close: |
| **Synchronization** [^3][^4]  | Binary/n-ary operators measuring alignment of signals (cross-correlation, phase-locking, group entrainment). | :material-close: |
| **Causality** [^4]            | Directional relationships (e.g., Granger causality, transfer entropy) to detect leader–follower dynamics.    | :material-close: |
| **Clusterability** [^5]       | Measures the tendency of data points to form clusters by means of the Hopkins statistics.                    | :material-close: |
| **Predictive Models**         | Hidden Markov Models, classifiers, neural networks; used for gesture segmentation or quality inference.      | :material-close: |
| **Saliency / Rarity** [^6]    | Detecting unusual occurrences in movement with respect to most frequent patterns.                            | :material-close: |


## References

[^1]: Glowinski, D., Mancini, M., & Camurri, A. (2013, March). Studying the effect of creative joint action on musicians’ behavior. In International Conference on Arts and Technology (pp. 113-119). Berlin, Heidelberg: Springer Berlin Heidelberg.
[^2]: Glowinski, D., Dael, N., Camurri, A., Volpe, G., Mortillaro, M., & Scherer, K. (2011). Toward a minimal representation of affective gestures. IEEE Transactions on Affective Computing, 2(2), 106-118.
[^3]: Varni, G., Volpe, G., & Camurri, A. (2010). A system for real-time multimodal analysis of nonverbal affective social interaction in user-centric media. IEEE Transactions on Multimedia, 12(6), 576-590.
[^4]: Sabharwal, S. R., Varlet, M., Breaden, M., Volpe, G., Camurri, A., & Keller, P. E. (2022). huSync-A model and system for the measure of synchronization in small groups: A case study on musical joint action. IEEE Access, 10, 92357-92372.
[^5]: Corbellini, N., Ceccaldi, E., Varni, G., & Volpe, G. (2022, August). An exploratory study on group potency classification from non-verbal social behaviours. In International Conference on Pattern Recognition (pp. 240-255). Cham: Springer Nature Switzerland.
[^6]: Niewiadomski, R., Mancini, M., Cera, A., Piana, S., Canepa, C., & Camurri, A. (2019). Does embodied training improve the recognition of mid-level expressive movement qualities sonification?. Journal on Multimodal User Interfaces, 13, 191-203.
