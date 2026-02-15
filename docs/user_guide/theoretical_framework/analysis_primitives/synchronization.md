# Synchronization Analysis Module

The **Synchronization Module** quantifies temporal coordination between multiple participants, body segments, or movement components.  
It provides methods to assess how well different movement signals align in **time** and **phase**.

!!! note
     The method assumes stationarity over the analysis window and Gaussian noise.

## Algorithms Details

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

[//]: # (## Usage Examples)

[//]: # ()
[//]: # (### Basic Synchronization Analysis)

[//]: # ()
[//]: # (```python)

[//]: # (from pyeyesweb.sync import Synchronization)

[//]: # (import numpy as np)

[//]: # ()
[//]: # (# Initialize synchronization analyzer)

[//]: # (sync_analyzer = Synchronization&#40;sampling_rate=100.0&#41;)

[//]: # ()
[//]: # (# Load two movement signals)

[//]: # (person1_velocity = np.load&#40;'person1_movement.npy'&#41;)

[//]: # (person2_velocity = np.load&#40;'person2_movement.npy'&#41;)

[//]: # ()
[//]: # (# Calculate cross-correlation)

[//]: # (correlation_metrics = sync_analyzer.calculate_cross_correlation&#40;)

[//]: # (    person1_velocity, person2_velocity)

[//]: # (&#41;)

[//]: # ()
[//]: # (print&#40;f"Max correlation: {correlation_metrics['max_correlation']:.3f}"&#41;)

[//]: # (print&#40;f"Optimal lag: {correlation_metrics['lag_seconds']:.3f} seconds"&#41;)

[//]: # ()
[//]: # (# Assess phase coupling)

[//]: # (phase_metrics = sync_analyzer.assess_phase_coupling&#40;)

[//]: # (    person1_velocity, person2_velocity)

[//]: # (&#41;)

[//]: # ()
[//]: # (print&#40;f"Phase locking value: {phase_metrics['phase_locking_value']:.3f}"&#41;)

[//]: # (```)

[//]: # ()
[//]: # (### Multi-Person Dance Analysis)

[//]: # ()
[//]: # (```python)

[//]: # (def analyze_dance_synchronization&#40;dancer_trajectories&#41;:)

[//]: # (    """Analyze synchronization between multiple dancers.""")

[//]: # (    sync_analyzer = Synchronization&#40;sampling_rate=60.0&#41;)

[//]: # (    n_dancers = len&#40;dancer_trajectories&#41;)

[//]: # (    )
[//]: # (    # Pairwise synchronization analysis)

[//]: # (    sync_matrix = np.zeros&#40;&#40;n_dancers, n_dancers&#41;&#41;)

[//]: # (    )
[//]: # (    for i in range&#40;n_dancers&#41;:)

[//]: # (        for j in range&#40;i+1, n_dancers&#41;:)

[//]: # (            # Extract velocity signals)

[//]: # (            vel_i = compute_velocity&#40;dancer_trajectories[i]&#41;)

[//]: # (            vel_j = compute_velocity&#40;dancer_trajectories[j]&#41;)

[//]: # (            )
[//]: # (            # Calculate synchronization)

[//]: # (            sync_metrics = sync_analyzer.calculate_cross_correlation&#40;)

[//]: # (                vel_i, vel_j)

[//]: # (            &#41;)

[//]: # (            )
[//]: # (            sync_matrix[i, j] = sync_metrics['max_correlation'])

[//]: # (            sync_matrix[j, i] = sync_matrix[i, j])

[//]: # (    )
[//]: # (    return {)

[//]: # (        'synchronization_matrix': sync_matrix,)

[//]: # (        'average_synchronization': np.mean&#40;sync_matrix[sync_matrix > 0]&#41;,)

[//]: # (        'most_synchronized_pair': np.unravel_index&#40;)

[//]: # (            np.argmax&#40;sync_matrix&#41;, sync_matrix.shape)

[//]: # (        &#41;)

[//]: # (    })

[//]: # (```)

[//]: # ()
[//]: # (### Bilateral Coordination Assessment)

[//]: # ()
[//]: # (```python)

[//]: # (def assess_bilateral_coordination&#40;left_limb_data, right_limb_data&#41;:)

[//]: # (    """Assess left-right limb coordination.""")

[//]: # (    sync_analyzer = Synchronization&#40;sampling_rate=100.0&#41;)

[//]: # (    )
[//]: # (    # Time-varying synchronization analysis)

[//]: # (    window_size = 200  # 2 seconds at 100 Hz)

[//]: # (    )
[//]: # (    sync_timeline = sync_analyzer.windowed_synchronization&#40;)

[//]: # (        left_limb_data, right_limb_data, )

[//]: # (        window_size=window_size,)

[//]: # (        overlap=0.75)

[//]: # (    &#41;)

[//]: # (    )
[//]: # (    # Identify coordination phases)

[//]: # (    high_sync_periods = sync_timeline['correlation'] > 0.7)

[//]: # (    low_sync_periods = sync_timeline['correlation'] < 0.3)

[//]: # (    )
[//]: # (    return {)

[//]: # (        'sync_timeline': sync_timeline,)

[//]: # (        'high_coordination_duration': np.sum&#40;high_sync_periods&#41; / 100.0,)

[//]: # (        'low_coordination_duration': np.sum&#40;low_sync_periods&#41; / 100.0,)

[//]: # (        'average_coordination': np.mean&#40;sync_timeline['correlation']&#41;)

[//]: # (    })

[//]: # (```)

[//]: # ()
[//]: # (### Real-Time Synchronization Monitoring)

[//]: # ()
[//]: # (```python)

[//]: # (class RealTimeSyncMonitor:)

[//]: # (    def __init__&#40;self, buffer_size=500, sampling_rate=50.0&#41;:)

[//]: # (        self.sync_analyzer = Synchronization&#40;sampling_rate=sampling_rate&#41;)

[//]: # (        self.buffer_size = buffer_size)

[//]: # (        self.buffer1 = deque&#40;maxlen=buffer_size&#41;)

[//]: # (        self.buffer2 = deque&#40;maxlen=buffer_size&#41;)

[//]: # (        )
[//]: # (    def update&#40;self, signal1_sample, signal2_sample&#41;:)

[//]: # (        """Update with new data samples.""")

[//]: # (        self.buffer1.append&#40;signal1_sample&#41;)

[//]: # (        self.buffer2.append&#40;signal2_sample&#41;)

[//]: # (        )
[//]: # (        if len&#40;self.buffer1&#41; == self.buffer_size:)

[//]: # (            # Calculate current synchronization)

[//]: # (            sync_metrics = self.sync_analyzer.calculate_cross_correlation&#40;)

[//]: # (                np.array&#40;self.buffer1&#41;,)

[//]: # (                np.array&#40;self.buffer2&#41;)

[//]: # (            &#41;)

[//]: # (            return sync_metrics)

[//]: # (        )
[//]: # (        return None)

[//]: # ()
[//]: # (# Usage in real-time system)

[//]: # (monitor = RealTimeSyncMonitor&#40;buffer_size=300&#41;)

[//]: # ()
[//]: # (for frame in motion_stream:)

[//]: # (    signal1 = extract_feature1&#40;frame&#41;)

[//]: # (    signal2 = extract_feature2&#40;frame&#41;)

[//]: # (    )
[//]: # (    sync_result = monitor.update&#40;signal1, signal2&#41;)

[//]: # (    )
[//]: # (    if sync_result and sync_result['max_correlation'] > 0.8:)

[//]: # (        print&#40;"High synchronization detected!"&#41;)

[//]: # (```)

[//]: # ()
[//]: # (## Integration with Other Modules)

[//]: # ()
[//]: # (### Combined with Smoothness Analysis)

[//]: # (```python)

[//]: # (# Assess both synchronization and smoothness)

[//]: # (sync_metrics = sync_analyzer.calculate_cross_correlation&#40;signal1, signal2&#41;)

[//]: # (smoothness_metrics = smoothness_analyzer&#40;[signal1, signal2]&#41;)

[//]: # ()
[//]: # (coordination_quality = {)

[//]: # (    'synchronization': sync_metrics['max_correlation'],)

[//]: # (    'smoothness': smoothness_metrics['sparc'],)

[//]: # (    'combined_score': &#40;sync_metrics['max_correlation'] + )

[//]: # (                      abs&#40;smoothness_metrics['sparc']&#41;&#41; / 2)

[//]: # (})

[//]: # (```)

[//]: # ()
[//]: # (### Integration with Bilateral Symmetry)

[//]: # (```python)

[//]: # (# Multi-level coordination analysis)

[//]: # (bilateral_metrics = symmetry_analyzer.calculate_symmetry_index&#40;)

[//]: # (    left_data, right_data)

[//]: # (&#41;)

[//]: # (temporal_sync = sync_analyzer.calculate_cross_correlation&#40;)

[//]: # (    left_data, right_data)

[//]: # (&#41;)

[//]: # ()
[//]: # (comprehensive_coordination = {)

[//]: # (    'spatial_symmetry': bilateral_metrics,)

[//]: # (    'temporal_synchronization': temporal_sync)

[//]: # (})

[//]: # (```)

## References

To be added