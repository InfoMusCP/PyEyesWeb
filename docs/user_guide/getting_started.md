<style>
  /* 1. Force the Description column (2nd column) to wrap text */
  .rst-content table.docutils td:nth-child(2) {
      white-space: normal !important;  /* Forces text to wrap */
      word-wrap: break-word !important;
      max-width: 300px !important;     /* Sets the constraint */
  }

 /* 2. Fix the Huge Icons */
  .rst-content .twemoji {
      height: 1.2em !important;
      width: 1.2em !important;
      vertical-align: text-bottom;
  }


</style>

# Getting Started

PyEyesWeb is an open-source Python library for the analysis of expressive qualities in human movement.
It provides algorithms to extract movement features from motion data, enabling researchers, artists, and developers to quantify and analyze movement expressivity.

## Installation

You can install PyEyesWeb using pip. Open your terminal and run:

```bash
pip install pyeyesweb
```

## Quick Start

Here's a simple example to get you started with PyEyesWeb. This example demonstrates how to compute the smoothness index from motion data.

!!!note 
    Motion data can vary significantly depending on the use case.  
    In this example, we assume a simplified scenario where you have a CSV file containing pre-calculated velocity modules. The file is structured with frames in rows and the velocity value in a single column. We will loop through this file row-by-row, update a sliding window, and compute smoothness in real-time.

```python
import csv
from pyeyesweb.data_models import SlidingWindow
from pyeyesweb.low_level import Smoothness

# 1. Initialize the Smoothness analyzer
smoothness = Smoothness(rate_hz=50.0)

# 2. Create a sliding window to store the last 100 frames of data
window = SlidingWindow(max_length=100, n_columns=1)

# 3. Simulate a real-time loop reading from a CSV
with open('velocity_data.csv', 'r') as f:
    reader = csv.reader(f)

    for row in reader:
        # Extract the velocity module (assuming it is in the first column)
        velocity_val = float(row[0])

        # Append the new frame to the sliding window
        window.append([velocity_val]) #(1)!

        # Compute smoothness features on the current window
        sparc, jerk = smoothness(window) #(2)!

        # Check if a valid result was returned 
        # (feature may return None if window has not enough samples)
        if sparc is not None and jerk is not None:
            print(f"SPARC: {sparc:.3f} | Jerk: {jerk:.3f}")
```

1. The `SlidingWindow` expects a list of values for every frame (even if there is only 1 sample). 
As the loop runs, new data is added to the end, and old data is automatically discarded once the max_length is reached.

2. The `smoothness` callable processes the current state of the window. 
It returns the SPARC (Spectral Arc Length) and Jerk RMS. 
If the window does not yet contain enough data to compute the metric, it may return None.

## Subpackages

PyEyesWeb is organized into subpackages analyzing movement features at different levels of abstraction and time scales [^1].

| <div style="min-width:150px">Subpackage</div>                                             | <div style="width:100px">Description</div>                                                                           |   Implemented    |
|:------------------------------------------------------------------------------------------|:---------------------------------------------------------------------------------------------------------------------|:----------------:|
| [`physical_signals`](theoretical_framework/physical_signals/physical_signals.md)          | Data acquisition from physical and virtual sensors (e.g., motion capture, IMU, video, physiological signals).        | :material-close: |
| [`low_level`](theoretical_framework/low_level/low_level.md)                               | Extraction of instantaneous descriptors from raw data (e.g., velocity, acceleration, kinetic energy, posture).       | :material-check: |
| [`mid_level`](theoretical_framework/mid_level/mid_level.md)                               | Structural and amodal descriptors over movement units or windows (e.g., fluidity, coordination, lightness).          | :material-check: |
| [`high_level`](theoretical_framework/high_level/high_level.md)                            | Expressive and communicative qualities perceived by an observer (e.g., emotion, saliency, social signals).           | :material-close: |
| [`analysis_primitives`](theoretical_framework/analysis_primitives/analysis_primitives.md) | General-purpose operators applied at all levels (e.g., statistical moments, entropy, recurrence, predictive models). | :material-check: |

## References

[^1]: Camurri, A., Volpe, G., Piana, S., Mancini, M., Niewiadomski, R., Ferrari, N., & Canepa, C. (2016, July). The dancer in the eye: towards a multi-layered computational framework of qualities in movement. In Proceedings of the 3rd International Symposium on Movement and Computing (pp. 1-7).