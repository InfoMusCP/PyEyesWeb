# Bilateral Symmetry Analysis Module

The Bilateral Symmetry module analyzes left-right coordination patterns using research-validated methods. Bilateral symmetry assessment is crucial for understanding movement disorders, rehabilitation progress, and motor control strategies.

## Overview

Bilateral symmetry analysis quantifies how well left and right body sides coordinate during movement. The module implements multiple complementary methods:

- **Canonical Correlation Analysis (CCA)**: Multivariate correlation between left-right trajectories
- **Phase Synchronization**: Temporal coordination using Hilbert transform
- **Coefficient of Variation**: Statistical symmetry indices
- **Cross-Correlation**: Temporal alignment analysis

## Algorithm Details

### Canonical Correlation Analysis (CCA)

CCA identifies linear combinations of left and right trajectories that maximize correlation:

1. Center and normalize trajectory data
2. Compute canonical variates using SVD
3. Extract first canonical correlation coefficient
4. Values range 0-1 (higher = more correlated)

### Phase Synchronization

Phase coupling analysis using analytic signal approach:

1. Apply Hilbert transform to extract instantaneous phases
2. Compute phase difference between left-right signals
3. Calculate phase locking value (PLV)
4. Assess consistency of phase relationships

### Coefficient of Variation Symmetry

Statistical approach comparing trajectory variability:

1. Compute coefficient of variation for each trajectory
2. Calculate ratio between left and right CV values
3. Transform to symmetry index (1.0 = perfect symmetry)

### Cross-Correlation Analysis

Temporal correlation with lag compensation:

1. Compute cross-correlation function
2. Identify maximum correlation value and corresponding lag
3. Assess temporal coordination quality

## Usage Examples

### Basic Symmetry Analysis

```python
from pyeyesweb.analysis_primitives.bilateral_symmetry import BilateralSymmetryAnalyzer
import numpy as np

# Initialize analyzer
symmetry_analyzer = BilateralSymmetryAnalyzer(window_size=100)

# Load bilateral trajectory data
left_arm = np.load('left_arm_trajectory.npy')  # Shape: (n_samples, 3)
right_arm = np.load('right_arm_trajectory.npy')  # Shape: (n_samples, 3)

# Calculate symmetry metrics
metrics = symmetry_analyzer.calculate_symmetry_index(left_arm, right_arm)

print(f"CCA Correlation: {metrics['cca_correlation']:.3f}")
print(f"Phase Synchronization: {metrics['phase_sync']:.3f}")
print(f"CV Symmetry: {metrics['cv_symmetry']:.3f}")
print(f"Phase Lag: {metrics['phase_lag']} samples")
```

### Gait Symmetry Analysis

```python
# Analyze walking symmetry
left_heel = extract_marker_trajectory('LEFT_HEEL', mocap_data)
right_heel = extract_marker_trajectory('RIGHT_HEEL', mocap_data)

gait_symmetry = symmetry_analyzer.calculate_symmetry_index(
    left_heel, right_heel
)

# Assess gait quality
if gait_symmetry['cca_correlation'] > 0.8:
    print("High bilateral coordination")
elif gait_symmetry['cca_correlation'] < 0.5:
    print("Potential coordination deficit")
```

### Real-Time Monitoring

```python
# Stream-based symmetry monitoring
symmetry_analyzer = BilateralSymmetryAnalyzer(window_size=50)

for frame in motion_stream:
    left_data = frame['left_markers']
    right_data = frame['right_markers']
    
    current_metrics = symmetry_analyzer.analyze_real_time(
        left_data, right_data
    )
    
    # Monitor symmetry changes
    if current_metrics['cca_correlation'] < threshold:
        trigger_alert("Asymmetry detected")
```

## Parameter Selection

### Window Size
- Minimum: 20 samples for stable CCA
- Typical range: 50-200 samples
- Longer windows: more stable metrics, less temporal resolution
- Shorter windows: higher sensitivity to transient asymmetries

### Overlap
- Higher overlap: smoother metric evolution
- Lower overlap: faster response to changes
- Recommended: 0.3-0.7 for most applications

## Interpretation Guidelines

### CCA Correlation
- Range: 0.0-1.0
- >0.8: Excellent bilateral coordination
- 0.6-0.8: Good coordination
- 0.4-0.6: Moderate coordination
- <0.4: Poor coordination

### Phase Synchronization
- Range: 0.0-1.0
- >0.7: Strong phase coupling
- 0.4-0.7: Moderate coupling
- <0.4: Weak or absent coupling

### CV Symmetry
- Range: 0.0-1.0
- 1.0: Perfect symmetry
- >0.8: Good symmetry
- 0.6-0.8: Moderate asymmetry
- <0.6: High asymmetry

### Phase Lag
- Units: samples (convert using sampling rate)
- Zero lag: synchronous movement
- Positive lag: left leads right
- Negative lag: right leads left

## Research Applications

### Neurological Assessment
Quantify bilateral deficits in:
- Stroke rehabilitation
- Parkinson's disease
- Cerebellar disorders
- Developmental coordination disorders

### Sports Biomechanics
Analyze bilateral coordination in:
- Running and gait analysis
- Swimming stroke mechanics
- Athletic skill assessment
- Injury risk evaluation

### Rehabilitation Monitoring
Track recovery through:
- Baseline symmetry assessment
- Intervention effectiveness
- Progress quantification
- Outcome prediction

## Research Foundation

Implementation based on:

1. **Bilateral Motion Data Fusion** (2018)
   - PubMed ID: 29993408
   - CCA methodology for bilateral coordination
   - Multi-dimensional trajectory analysis

2. **Wheelchair Propulsion Symmetry** (2022)
   - MDPI Symmetry Journal
   - Coefficient of variation approach
   - Real-world validation studies

3. **Phase Synchronization Methods**
   - Hilbert transform applications
   - Phase locking value calculations
   - Neurophysiological coordination studies

## Limitations and Considerations

### Data Requirements
- Minimum 20 samples for stable analysis
- Matched sampling rates for bilateral data
- Consistent coordinate systems

### Methodological Assumptions
- Linear relationships in CCA analysis
- Stationarity for phase analysis
- Gaussian noise assumptions

### Interpretation Context
- Task-specific symmetry expectations
- Individual variation considerations
- Pathology-specific patterns

## References

To be added