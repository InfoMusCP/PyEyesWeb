# Smoothness Analysis Module

The Smoothness module quantifies control using established motor control metrics.
Smooth movements are characterized by continuous, coordinated trajectories with minimal abrupt changes.

The module implements two primary metrics validated in motor control research [^1]:

- **Spectral Arc Length (SPARC)**: frequency domain smoothness measure.
- **Jerk Root Mean Square (RMS)**: time domain measure based on movement derivatives.

<span style="color:#d32f2f; font-weight:bold;">
This metric has been used for... **ADD PAPERS**
</span>

## Algorithms Details

### SPARC Calculation

The **Spectral Arc Length (SPARC)** quantifies movement smoothness by measuring the arc length of the normalized power spectral density (PSD) of the velocity profile.

1. **Compute the power spectral density (PSD)**  
   Using Welch's method, obtain the PSD of the velocity signal \( v(t) \):

$$
P(f) = \text{WelchPSD}[v(t)]
$$

<ol start="2">
<li>
<strong>Normalize the PSD</strong>  
<br>Normalize frequency and magnitude to unit range:  
</li>
</ol>  

$$
\hat{f} \in [0,1], \quad \hat{P}(\hat{f}) = \frac{P(f)}{\max P(f)}
$$

<ol start="3">
<li>
<strong>Calculate arc length</strong>  
<br>The spectral arc length is:   
</li>
</ol> 

$$
L = \sum_{i=1}^{N-1} \sqrt{\big(\hat{f}_{i+1}-\hat{f}_i\big)^2 + \big(\hat{P}(\hat{f}_{i+1})-\hat{P}(\hat{f}_i)\big)^2}
$$

<ol start="4">
<li>
<strong>Return negative arc length</strong>  
<br>Define SPARC as:   
</li>
</ol>  

$$
\text{SPARC} = -L
$$

!!! tip
    SPARC values typically range from -1.5 to -6.0, where **more negative values indicate smoother motion**.  
    Values > -1.5 may indicate very jerky movement, while values < -6.0 may suggest over-smoothed or artificial data.

---

### Jerk RMS Calculation

The **Jerk Root Mean Square (RMS)** measures smoothness as the average magnitude of the third derivative of position.

1. **Compute velocity** from position \( x(t) \): 

$$
v(t) = \frac{dx(t)}{dt}
$$

<ol start="2">
<li>
<strong>Compute acceleration</strong>:   
</li>
</ol> 

$$
a(t) = \frac{dv(t)}{dt}
$$

<ol start="3">
<li>
<strong>Compute jerk</strong>:  
</li>
</ol>  

$$
j(t) = \frac{da(t)}{dt} = \frac{d^3 x(t)}{dt^3}
$$

<ol start="4">
<li>
<strong>Calculate RMS of jerk values</strong>:  
<br>For \(N\) samples,
</li>
</ol> 

$$
\text{RMS}_j = \sqrt{\frac{1}{N}\sum_{i=1}^{N} j(t_i)^2}
$$

!!! tip
    The measurment units is (length unit)/s³ (e.g., m/s³).  
    Lower RMS values indicate smoother movement, but the scale depends on movement amplitude and units.

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

## References

[^1]: TODO