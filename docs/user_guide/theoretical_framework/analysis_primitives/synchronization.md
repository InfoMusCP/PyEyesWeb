# Synchronization Analysis Module

The **Synchronization Module** quantifies temporal coordination between multiple participants, body segments, or movement components.  
It provides methods to assess how well different movement signals align in **time** and **phase**.

The module implements validated methods for temporal coordination assessment including:
- cross-correlation with lag analysis.
- Phase coupling and Phase Locking Values (PLV).

!!! note
     These methods assume stationarity over the analysis window and Gaussian noise.

## Algorithms Details

### Cross-Correlation Analysis

Cross-correlation quantifies linear similarity between signals as a function of lag:

$$
R_{xy}(\tau) = \frac{\sum_t (x(t)-\bar{x})(y(t+\tau)-\bar{y})}{\sigma_x \sigma_y}
$$

- \( \tau \) is the lag  
- \( R_{xy}(\tau) \in [-1,1] \)  

**Output:**

$$
\rho_{\max} = \max_\tau R_{xy}(\tau), \quad \tau^* = \arg\max_\tau R_{xy}(\tau)
$$

!!! tip "Interpretation"
    | Synchronization Strength                                   | Lag Interpretation                                                                  |
    |------------------------------------------------------------|-------------------------------------------------------------------------------------|
    | \( \rho_{\max} > 0.8 \): excellent synchronization         | **Zero lag (\(\tau \approx 0\))**: Signals are perfectly in-phase                   |
    | \( 0.6 < \rho_{\max} \leq 0.8 \): good synchronization     | **Positive lag (\(\tau > 0\))**: Signal2 leads Signal1 by \(\tau\) seconds          |
    | \( 0.4 < \rho_{\max} \leq 0.6 \): moderate synchronization | **Negative lag (\(\tau < 0\))**: Signal1 leads Signal2 by \(\tau\) seconds          |
    | \( \rho_{\max} \leq 0.4 \): poor synchronization           | **Large lag (\(\tau > T_{threshold}\))**: Loose coordination or potential artifacts |


### Phase Coupling Analysis

Phase synchronization measures temporal alignment independent of amplitude:

1. **Hilbert Transform**: Compute analytic signals  

$$
z_x(t) = x(t) + i H[x(t)], \quad z_y(t) = y(t) + i H[y(t)]
$$

2. **Instantaneous Phases**:

$$
\phi_x(t) = \arg(z_x(t)), \quad \phi_y(t) = \arg(z_y(t))
$$

3. **Phase Difference**:

$$
\Delta \phi(t) = \phi_x(t) - \phi_y(t)
$$

4. **Phase Locking Value (PLV)**:

$$
\text{PLV} = \left| \frac{1}{N} \sum_{t=1}^{N} e^{i \Delta \phi(t)} \right|
$$

**Output:** \( \text{PLV} \in [0,1] \)

!!! tip "Interpretation"
    - \( PLV > 0.7 \): strong phase coupling
    - \( 0.4 < PLV \leq 0.7 \): moderate phase coupling
    - \( PLV \leq 0.4 \): weak phase coupling 

## Usage Examples

### Basic Synchronization Analysis

```python
from pyeyesweb.analysis_primitives.synchronization import Synchronization
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

## References

To be added