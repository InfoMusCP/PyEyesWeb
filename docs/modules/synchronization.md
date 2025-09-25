# Synchronization Analysis Module

The Synchronization module quantifies temporal coordination between multiple participants, body segments, or movement components. It provides methods to assess how well different movement signals align in time and phase.

## Overview

Movement synchronization analysis is essential for understanding:
- Multi-person coordination (e.g., dance, sports teams)
- Inter-limb coordination (e.g., bilateral arm movements)
- Multi-joint coordination patterns
- Temporal coupling in rehabilitation settings

The module implements validated methods for temporal coordination assessment including cross-correlation, phase coherence, and lag analysis.

## Class: `Synchronization`

### Constructor

```python
Synchronization(sampling_rate=50.0, max_lag=None)
```

**Parameters:**
- `sampling_rate` (float): Data sampling frequency in Hz
- `max_lag` (int): Maximum lag for cross-correlation analysis

### Methods

#### `calculate_cross_correlation(signal1, signal2)`

Computes cross-correlation between two signals to assess temporal coordination.

**Parameters:**
- `signal1` (ndarray): First signal time series
- `signal2` (ndarray): Second signal time series

**Returns:**
Dictionary containing:
- `'max_correlation'`: Peak cross-correlation value
- `'lag_samples'`: Lag at maximum correlation (in samples)
- `'lag_seconds'`: Lag at maximum correlation (in seconds)
- `'correlation_curve'`: Full cross-correlation function

#### `assess_phase_coupling(signal1, signal2)`

Analyzes phase relationships between signals using Hilbert transform.

**Parameters:**
- `signal1` (ndarray): First signal time series
- `signal2` (ndarray): Second signal time series

**Returns:**
Dictionary containing:
- `'phase_locking_value'`: Phase coupling strength (0-1)
- `'mean_phase_diff'`: Average phase difference
- `'phase_consistency'`: Consistency of phase relationship

#### `windowed_synchronization(signal1, signal2, window_size, overlap=0.5)`

Computes time-varying synchronization using sliding windows.

**Parameters:**
- `signal1`, `signal2` (ndarray): Input signals
- `window_size` (int): Analysis window length
- `overlap` (float): Window overlap fraction

**Returns:**
Time series of synchronization metrics

## Algorithm Details

### Cross-Correlation Analysis

Cross-correlation quantifies linear similarity between signals as a function of lag:

```
R(τ) = Σ(x(t) * y(t+τ)) / √(Σx²(t) * Σy²(t))
```

Where:
- τ is the lag parameter
- R(τ) ranges from -1 to +1
- Maximum |R(τ)| indicates optimal temporal alignment

### Phase Coupling Analysis

Phase relationships assessed using analytic signals:

1. **Hilbert Transform**: Extract instantaneous phases
2. **Phase Difference**: Compute φ₁(t) - φ₂(t)
3. **Phase Locking Value**: Assess phase consistency

PLV calculation:
```
PLV = |⟨e^(i*Δφ(t))⟩|
```

### Windowed Analysis

Time-varying synchronization using overlapping windows:
- Maintains temporal resolution
- Captures dynamic coordination changes
- Provides statistical stability

## Usage Examples

### Basic Synchronization Analysis

```python
from pyeyesweb.sync import Synchronization
import numpy as np

# Initialize synchronization analyzer
sync_analyzer = Synchronization(sampling_rate=100.0)

# Load two movement signals
person1_velocity = np.load('person1_movement.npy')
person2_velocity = np.load('person2_movement.npy')

# Calculate cross-correlation
correlation_metrics = sync_analyzer.calculate_cross_correlation(
    person1_velocity, person2_velocity
)

print(f"Max correlation: {correlation_metrics['max_correlation']:.3f}")
print(f"Optimal lag: {correlation_metrics['lag_seconds']:.3f} seconds")

# Assess phase coupling
phase_metrics = sync_analyzer.assess_phase_coupling(
    person1_velocity, person2_velocity
)

print(f"Phase locking value: {phase_metrics['phase_locking_value']:.3f}")
```

### Multi-Person Dance Analysis

```python
def analyze_dance_synchronization(dancer_trajectories):
    """Analyze synchronization between multiple dancers."""
    sync_analyzer = Synchronization(sampling_rate=60.0)
    n_dancers = len(dancer_trajectories)
    
    # Pairwise synchronization analysis
    sync_matrix = np.zeros((n_dancers, n_dancers))
    
    for i in range(n_dancers):
        for j in range(i+1, n_dancers):
            # Extract velocity signals
            vel_i = compute_velocity(dancer_trajectories[i])
            vel_j = compute_velocity(dancer_trajectories[j])
            
            # Calculate synchronization
            sync_metrics = sync_analyzer.calculate_cross_correlation(
                vel_i, vel_j
            )
            
            sync_matrix[i, j] = sync_metrics['max_correlation']
            sync_matrix[j, i] = sync_matrix[i, j]
    
    return {
        'synchronization_matrix': sync_matrix,
        'average_synchronization': np.mean(sync_matrix[sync_matrix > 0]),
        'most_synchronized_pair': np.unravel_index(
            np.argmax(sync_matrix), sync_matrix.shape
        )
    }
```

### Bilateral Coordination Assessment

```python
def assess_bilateral_coordination(left_limb_data, right_limb_data):
    """Assess left-right limb coordination."""
    sync_analyzer = Synchronization(sampling_rate=100.0)
    
    # Time-varying synchronization analysis
    window_size = 200  # 2 seconds at 100 Hz
    
    sync_timeline = sync_analyzer.windowed_synchronization(
        left_limb_data, right_limb_data, 
        window_size=window_size,
        overlap=0.75
    )
    
    # Identify coordination phases
    high_sync_periods = sync_timeline['correlation'] > 0.7
    low_sync_periods = sync_timeline['correlation'] < 0.3
    
    return {
        'sync_timeline': sync_timeline,
        'high_coordination_duration': np.sum(high_sync_periods) / 100.0,
        'low_coordination_duration': np.sum(low_sync_periods) / 100.0,
        'average_coordination': np.mean(sync_timeline['correlation'])
    }
```

### Real-Time Synchronization Monitoring

```python
class RealTimeSyncMonitor:
    def __init__(self, buffer_size=500, sampling_rate=50.0):
        self.sync_analyzer = Synchronization(sampling_rate=sampling_rate)
        self.buffer_size = buffer_size
        self.buffer1 = deque(maxlen=buffer_size)
        self.buffer2 = deque(maxlen=buffer_size)
        
    def update(self, signal1_sample, signal2_sample):
        """Update with new data samples."""
        self.buffer1.append(signal1_sample)
        self.buffer2.append(signal2_sample)
        
        if len(self.buffer1) == self.buffer_size:
            # Calculate current synchronization
            sync_metrics = self.sync_analyzer.calculate_cross_correlation(
                np.array(self.buffer1),
                np.array(self.buffer2)
            )
            return sync_metrics
        
        return None

# Usage in real-time system
monitor = RealTimeSyncMonitor(buffer_size=300)

for frame in motion_stream:
    signal1 = extract_feature1(frame)
    signal2 = extract_feature2(frame)
    
    sync_result = monitor.update(signal1, signal2)
    
    if sync_result and sync_result['max_correlation'] > 0.8:
        print("High synchronization detected!")
```

## Parameter Selection

### Sampling Rate
- Match your data acquisition frequency
- Higher rates improve lag resolution
- Consider computational requirements for real-time analysis

### Maximum Lag
- Default: 25% of signal length
- Longer lags: capture larger temporal offsets
- Shorter lags: focus on tight synchronization

### Window Size (for windowed analysis)
- Minimum: 50-100 samples for stable estimates
- Typical: 2-10 seconds of data
- Longer windows: more stable metrics, less temporal resolution

## Interpretation Guidelines

### Cross-Correlation Values
- **r > 0.8**: Excellent synchronization
- **0.6 < r ≤ 0.8**: Good synchronization  
- **0.4 < r ≤ 0.6**: Moderate synchronization
- **r ≤ 0.4**: Poor synchronization

### Phase Locking Values
- **PLV > 0.7**: Strong phase coupling
- **0.4 < PLV ≤ 0.7**: Moderate coupling
- **PLV ≤ 0.4**: Weak coupling

### Lag Interpretation
- **Zero lag**: Perfectly in-phase coordination
- **Positive lag**: Signal2 leads Signal1
- **Negative lag**: Signal1 leads Signal2
- **Large lags**: May indicate loose coordination or artifacts

## Research Applications

### Interpersonal Coordination
- Joint action tasks
- Social motor coordination
- Music and dance performance
- Therapeutic interventions

### Motor Control Studies
- Bilateral coordination assessment
- Inter-limb coupling analysis
- Coordination development
- Neurological coordination deficits

### Rehabilitation Research
- Coordination training effectiveness
- Recovery assessment
- Biofeedback applications
- Adaptive therapy protocols

## Integration with Other Modules

### Combined with Smoothness Analysis
```python
# Assess both synchronization and smoothness
sync_metrics = sync_analyzer.calculate_cross_correlation(signal1, signal2)
smoothness_metrics = smoothness_analyzer([signal1, signal2])

coordination_quality = {
    'synchronization': sync_metrics['max_correlation'],
    'smoothness': smoothness_metrics['sparc'],
    'combined_score': (sync_metrics['max_correlation'] + 
                      abs(smoothness_metrics['sparc'])) / 2
}
```

### Integration with Bilateral Symmetry
```python
# Multi-level coordination analysis
bilateral_metrics = symmetry_analyzer.calculate_symmetry_index(
    left_data, right_data
)
temporal_sync = sync_analyzer.calculate_cross_correlation(
    left_data, right_data
)

comprehensive_coordination = {
    'spatial_symmetry': bilateral_metrics,
    'temporal_synchronization': temporal_sync
}
```

## Performance Considerations

- **Memory usage**: Scales with signal length and number of lags
- **Computational complexity**: O(n log n) for FFT-based correlation
- **Real-time constraints**: Buffer management and update frequency
- **Numerical stability**: Normalization and outlier handling

## References

To be added