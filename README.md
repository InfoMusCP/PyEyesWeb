# PyEyesWeb
## Quantitative movement analysis toolkit

PyEyesWeb is a research toolkit for extracting quantitative features from human movement data. It offers computational methods to analyze different qualities of movement. The repository is still in development, with the goal of creating an easy-to-use library for extracting movement qualities from raw motion data.

## Overview

Movement analysis involves extracting meaningful features from high-dimensional spatiotemporal data. PyEyesWeb provides computational methods to quantify movement characteristics at multiple levels, from basic kinematics to complex coordination patterns.

At the moment, this toolkit addresses four key movement qualities:
- **Smoothness**: Measuring smoothness and control with SPARC and jerk-based metrics
- **Bilateral symmetry**: Analyzing left-right coordination through canonical correlation analysis and phase synchronization
- **Contration-Expansion Index**: Measuring contraction and expansion patterns in movement trajectories
- **Synchronization Index**: Assessing synchronization between multiple participants or body segments

## Installation

```bash
git clone https://github.com/InfoMusCP/PyEyesWeb.git
cd PyEyesWeb
pip install -e .

# For development
pip install -e .[dev]
```

## Quick start

```python
from pyeyesweb import Smoothness, BilateralSymmetryAnalyzer
from pyeyesweb.data_models.sliding_window import SlidingWindow
import numpy as np

# Movement smoothness analysis
smoothness = Smoothness(rate_hz=50.0)
window = SlidingWindow(window_size=100)
window.add_frame(motion_data)

metrics = smoothness(window)
print(f"SPARC: {metrics['sparc']}, Jerk RMS: {metrics['jerk_rms']}")

# Bilateral symmetry analysis
symmetry_analyzer = BilateralSymmetryAnalyzer()
symmetry_index = symmetry_analyzer.calculate_symmetry_index(
    left_trajectory, right_trajectory
)
```

## Core Modules

### Smoothness Analysis
Movement smoothness quantification using a few metrics such as:
- SPARC (Spectral Arc Length)
- Root mean square jerk

We also use Savitzky-Golay filtering to smoothen signals.

### Bilateral Symmetry Analysis
Research-validated methods for bilateral coordination assessment:
- Canonical Correlation Analysis (CCA)
- Phase synchronization using Hilbert transform
- Coefficient of variation-based symmetry indices

Based on methodology from:
- Bilateral motion data fusion research (Pubmed: 29993408)
- Wheelchair propulsion symmetry analysis (MDPI Symmetry, 2022)

### Contraction/Expansion Analysis
Geometric analysis of spatial movement patterns:
- Numba-optimized area and volume calculations
- Real-time contraction/expansion rate computation
- 2D and 3D spatial pattern detection

### Synchronization Analysis
Multi-participant coordination measurement:
- Cross-correlation analysis
- Temporal alignment algorithms
- Phase coherence metrics

### TSV Reader
Efficient motion capture data processing:
- TSV file parsing
- Data integrity check
- Memory-efficient streaming

## Proposed Analysis Framework

The toolkit is designed to grow over time, with analyses organized into three levels: low, mid, and high. Each level builds on the one below it, moving from raw measurements to processed characteristics and finally to complex patterns of coordination.

### Low-Level Features
These include fundamental measurements captured directly from motion data:
- Position, velocity, and acceleration trajectories
- Joint angles and angular velocities
- Derivative-based measures such as jerk

### Mid-Level Features
These are derived characteristics that describe how movements are performed:
- Smoothness indices that reflect control and fluidity
- Symmetry coefficients comparing left and right sides
- Spatial metrics capturing contraction, expansion, and trajectory patterns
- Phase relationships between different body parts

### High-Level Features
These include complex patterns that emerge from coordination and strategy:
- Synchronization between multiple participants
- Quality of bilateral coordination
- Classification of overall movement strategies
- Recognition of recurring temporal patterns

## Documentation Structure

| Resource | Content |
|----------|---------|
| [Installation Guide](docs/installation.md) | Dependencies and setup procedures |
| [Module Documentation](docs/modules/README.md) | Detailed module descriptions |

## Research Applications

### Movement Disorder Assessment
```python
smoothness_analyzer = Smoothness(rate_hz=100.0)
patient_metrics = smoothness_analyzer(patient_data)
# Quantify movement deficits in neurological conditions
```

### Biomechanical Analysis
```python
symmetry_analyzer = BilateralSymmetryAnalyzer()
bilateral_coordination = symmetry_analyzer.analyze_gait_symmetry(
    left_limb_data, right_limb_data
)
# Assess gait asymmetries and compensation patterns
```

### Motor Learning Studies
```python
coordination_tracker = SynchronizationAnalyzer()
learning_progress = coordination_tracker.track_skill_acquisition(
    baseline_data, training_data
)
# Monitor coordination improvements during skill acquisition
```

## Methodological Foundation

PyEyesWeb implements peer-reviewed computational methods from:
- Motor control and biomechanics literature
- Signal processing, multivariate stats and time series analysis
- Computational geometry and spatial analysis

We are working on having parameter validation and numerical stability checks for all algorithms in this repository.

## License

MIT License
