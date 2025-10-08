# Getting Started

PyEyesWeb is an open-source Python library for the analysis of expressive qualities in human movement.
It provides algorithms to extract movement features from motion data, enabling researchers, artists, and developers to quantify and analyze movement expressivity.

## Installation

You can install PyEyesWeb using pip. Open your terminal and run:

```bash
pip install pyeyesweb
```

## Quick Start

Here's a simple example to get you started with PyEyesWeb. This example demonstrates how to load motion data and extract basic movement features.

```python
from pyeyesweb.data_models import SlidingWindow
from pyeyesweb.low_level import Smoothness

# Movement smoothness analysis
smoothness = Smoothness(rate_hz=50.0)
window = SlidingWindow(max_length=100, n_columns=1)
window.append([motion_data]) #(1)!

sparc, jerk = smoothness(window)
```

1. Here, `motion_data` should be replaced with your actual motion data input within a loop. For this example, we assume it's a single sample of motion data (e.g., x coordinate at time t).

## Subpackages

PyEyesWeb is organized into subpackages analyzing movement features at different levels of abstraction and time scales [^1].

| <div style="min-width:150px">Subpackage</div>                    | Description                                                                                                          | Implemented      |
|------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------|------------------|
| [`physical_signals`](theoretical_framework/physical_signals/index.md)       | Data acquisition from physical and virtual sensors (e.g., motion capture, IMU, video, physiological signals).        | :material-close: |
| [`low_level`](theoretical_framework/low_level/index.md)                     | Extraction of instantaneous descriptors from raw data (e.g., velocity, acceleration, kinetic energy, posture).       | :material-check: |
| [`mid_level`](theoretical_framework/mid_level/index.md)                     | Structural and amodal descriptors over movement units or windows (e.g., fluidity, coordination, lightness).          | :material-check: |
| [`high_level`](theoretical_framework/high_level/index.md)                   | Expressive and communicative qualities perceived by an observer (e.g., emotion, saliency, social signals).           | :material-close: |
| [`analysis_primitives`](theoretical_framework/analysis_primitives/index.md) | General-purpose operators applied at all levels (e.g., statistical moments, entropy, recurrence, predictive models). | :material-check: |

## References

[^1]: Camurri, A., Volpe, G., Piana, S., Mancini, M., Niewiadomski, R., Ferrari, N., & Canepa, C. (2016, July). The dancer in the eye: towards a multi-layered computational framework of qualities in movement. In Proceedings of the 3rd International Symposium on Movement and Computing (pp. 1-7).