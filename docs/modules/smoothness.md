# Smoothness Analysis Module

The Smoothness module quantifies movement fluidity and control using established motor control metrics. Smooth movements are characterized by continuous, coordinated trajectories with minimal abrupt changes.

## Overview

Movement smoothness analysis provides insight into motor control quality and neuromotor function. The module implements two primary metrics validated in motor control research:

- **SPARC (Spectral Arc Length)**: Frequency domain smoothness measure
- **Jerk RMS**: Time domain measure based on movement derivatives

## Class: `Smoothness`

### Constructor

```python
Smoothness(rate_hz=50.0, use_filter=True)
```

**Parameters:**
- `rate_hz` (float): Sampling frequency in Hz
- `use_filter` (bool): Enable Savitzky-Golay filtering

### Methods

#### `__call__(sliding_window: SlidingWindow)`

Computes smoothness metrics for windowed motion data.

**Parameters:**
- `sliding_window`: SlidingWindow object containing motion trajectories

**Returns:**
Dictionary containing:
- `'sparc'`: SPARC smoothness value (lower = smoother)
- `'jerk_rms'`: RMS jerk value (lower = smoother)
- `'filtered_signal'`: Processed signal array (if filtering enabled)

## Algorithm Details

### SPARC Calculation

SPARC measures the arc length of the power spectral density curve:

1. Compute power spectral density using Welch's method
2. Calculate arc length of normalized PSD curve
3. Return negative arc length (more negative = smoother)

### Jerk RMS Calculation

Root mean square of the third derivative (jerk):

1. Compute velocity from position data
2. Compute acceleration from velocity
3. Compute jerk from acceleration
4. Calculate RMS of jerk values

### Filtering

Optional Savitzky-Golay filter preprocessing:
- Reduces high-frequency noise
- Preserves signal features
- Adaptive window sizing based on sampling rate

## Usage Examples

### Basic Smoothness Analysis

```python
from pyeyesweb import Smoothness
from pyeyesweb.data_models.sliding_window import SlidingWindow
import numpy as np

# Initialize analyzer
smoothness = Smoothness(rate_hz=100.0)
window = SlidingWindow(window_size=200)

# Add motion data (3D coordinates)
for frame in motion_data:
    window.add_frame(frame)
    
    if len(window) >= 5:  # Minimum data requirement
        metrics = smoothness(window)
        print(f"SPARC: {metrics['sparc']:.3f}")
        print(f"Jerk RMS: {metrics['jerk_rms']:.3f}")
```

### Comparative Analysis

```python
# Compare smoothness across conditions
conditions = ['baseline', 'fatigue', 'recovery']
smoothness_data = {}

for condition in conditions:
    data = load_condition_data(condition)
    metrics = smoothness(data)
    smoothness_data[condition] = metrics['sparc']

# Lower SPARC values indicate smoother movement
print(f"Smoothest condition: {min(smoothness_data, key=smoothness_data.get)}")
```

## Parameter Selection

### Sampling Rate
- Match your motion capture system frequency
- Higher rates (>100 Hz) improve jerk calculation accuracy
- Lower rates may miss high-frequency movement components

### Window Size
- Minimum 5 samples for computation
- Typical range: 50-200 samples
- Longer windows: more stable metrics, less temporal resolution
- Shorter windows: higher temporal resolution, more variability

### Filtering
- Enable for noisy data (recommended)
- Disable for pre-filtered signals
- May affect jerk calculations in high-noise conditions

## Interpretation Guidelines

### SPARC Values
- Range: Typically -1.5 to -6.0
- More negative = smoother movement
- Values > -1.5 may indicate very jerky movement
- Values < -6.0 may indicate over-smoothed or artificial data

### Jerk RMS Values
- Units: (length units) / time³
- Lower values = smoother movement
- Scale depends on movement amplitude and units
- Compare relative values within experiments

## Research Applications

### Movement Disorders
Quantify movement deficits in:
- Parkinson's disease
- Essential tremor
- Dystonia
- Stroke recovery

### Motor Learning
Track skill acquisition through:
- Smoothness improvements over training
- Performance plateau identification
- Inter-individual variability analysis

### Rehabilitation Assessment
Monitor recovery progress via:
- Baseline smoothness measurement
- Intervention effectiveness
- Long-term outcome tracking

## References

To be added