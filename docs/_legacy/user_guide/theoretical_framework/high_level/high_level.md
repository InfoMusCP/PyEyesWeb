<style>
  /* 1. First Column: Allow wrapping and set modest width */
  .rst-content table.docutils td:nth-child(1) {
      width: 20%;              /* Fixed width for the feature name */
      white-space: normal !important; /* ALLOWS wrapping */
      word-wrap: break-word;   /* Breaks long words if necessary */
  }

  /* 2. Second Column: Maximize width */
  .rst-content table.docutils td:nth-child(2) {
      white-space: normal !important;
      word-wrap: break-word !important;
      width: 65%;              /* Takes up the majority of the table */
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

# Layer 4 – Expressive Qualities

The highest layer focuses on **how an observer perceives movement**, connecting computational features with **human-centered interpretation**.  
It addresses **nonverbal communication, emotions, and intentions** conveyed through movement, supporting **cross-modal experiences** (e.g., “listening to a choreography”)
and enabling applications in **art, therapy, rehabilitation, and HCI**

!!! note "Key Concepts"
    - **Observer perspective**: perception, not physical effort, defines qualities.
    - **Memory and context**: recent history influences interpretation (e.g., expectancy, contrast, saliency).
    - **Machine learning**: used to map mid-level trajectories to expressive qualities.

## Examples of Expressive Qualities

| Quality                         | Description                                                                           | Implemented      |
|---------------------------------|---------------------------------------------------------------------------------------|------------------|
| **Predictability / Expectancy** | Extent to which movement can be anticipated by an observer.                           | :material-close: |
| **Hesitation**                  | When intention behind movement is unclear to an observer.                             | :material-close: |
| **Attraction / Repulsion**      | Degree to which an observer feels drawn to or repelled by the movement.               | :material-close: |
| **Groove**                      | Extent to which movement elicits movement in the observer.                            | :material-close: |
| **Saliency**[^1]                    | How a movement stands out compared to others in context.                              | :material-close: |
| **Emotion**                     | Expressive emotional content conveyed via body movement (categorical or dimensional). | :material-close: |

---

## References

[^1]: Romano, G., Rajeev Sabharwal, S., Gnecco, G., Camurri, A. (2025). A Computational Framework for Identifying Salient Moments in Motion Capture Data. In: Nicosia, G., Ojha, V., Giesselbach, S., Pardalos, M.P., Umeton, R. (eds) Machine Learning, Optimization, and Data Science. LOD ACAIN 2024 2024. Lecture Notes in Computer Science, vol 15509. Springer, Cham. [:material-link-variant:](https://doi.org/10.1007/978-3-031-82484-5_20)

