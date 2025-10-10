# Smoothness Analysis Module

The Smoothness module quantifies control using established motor control metrics.
Smooth movements are characterized by continuous, coordinated trajectories with minimal abrupt changes.

The module implements two primary metrics validated in motor control research [^1]:

- **Spectral Arc Length (SPARC)**: frequency domain smoothness measure.
- **Jerk Root Mean Square (RMS)**: time domain measure based on movement derivatives.


## Algorithms Details

### SPARC Calculation

The **Spectral Arc Length (SPARC)** quantifies movement smoothness by measuring the arc length of the **normalized Fourier magnitude spectrum** of the signal.

1. **Compute the Fourier magnitude spectrum**  
   Take the Fast Fourier Transform (FFT) of the input signal \( s(t) \) and keep only the positive frequencies:

$$
Y(f) = |\text{FFT}[s(t)]|_{f > 0}
$$

<ol start="2">
<li>
<strong>Normalize the spectrum</strong>  
<br>Normalize the magnitude by its maximum value:
</li>
</ol>

$$
\hat{Y}(f) = \frac{Y(f)}{\max(Y(f))}
$$

<ol start="3">
<li>
<strong>Calculate arc length</strong>  
<br>Compute the total Euclidean arc length of the normalized spectrum:
</li>
</ol>

$$
L = \sum_{i=1}^{N-1} \sqrt{(f_{i+1} - f_i)^2 + (\hat{Y}_{i+1} - \hat{Y}_i)^2}
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
    SPARC values are **negative**, where more negative values indicate **smoother movement**.  
    Constant signals or signals with no variation return *NaN* (undefined smoothness).

---

### Jerk RMS Calculation

The **Jerk Root Mean Square (RMS)** measures smoothness as the average magnitude of the **finite-difference derivative** of the signal.

1. **Compute discrete derivative**  
   Approximate the first derivative using finite differences with sampling rate \( f_s \):

$$
j_i = \frac{s_{i+1} - s_i}{1 / f_s}
$$

<ol start="2">
<li>
<strong>Compute RMS of derivative (jerk) values</strong>:  
<br>For <i>N</i> samples,
</li>
</ol>

$$
\text{RMS}_j = \sqrt{\frac{1}{N} \sum_{i=1}^{N} j_i^2}
$$

!!! tip
    Lower RMS jerk values indicate smoother motion.  
    In this implementation, the function directly differentiates the provided signal once.
    Hence, the algorithm expects to receive **accelerations** as input; if you input **position**, you get **velocity RMS**.

[//]: # (## Usage Examples)

[//]: # ()
[//]: # (### Basic Smoothness Analysis)

[//]: # ()
[//]: # (```python)

[//]: # (from pyeyesweb import Smoothness)

[//]: # (from pyeyesweb.data_models.sliding_window import SlidingWindow)

[//]: # (import numpy as np)

[//]: # ()
[//]: # (# Initialize analyzer)

[//]: # (smoothness = Smoothness&#40;rate_hz=100.0&#41;)

[//]: # (window = SlidingWindow&#40;window_size=200&#41;)

[//]: # ()
[//]: # (# Add motion data &#40;3D coordinates&#41;)

[//]: # (for frame in motion_data:)

[//]: # (    window.add_frame&#40;frame&#41;)

[//]: # (    )
[//]: # (    if len&#40;window&#41; >= 5:  # Minimum data requirement)

[//]: # (        metrics = smoothness&#40;window&#41;)

[//]: # (        print&#40;f"SPARC: {metrics['sparc']:.3f}"&#41;)

[//]: # (        print&#40;f"Jerk RMS: {metrics['jerk_rms']:.3f}"&#41;)

[//]: # (```)

[//]: # ()
[//]: # (### Comparative Analysis)

[//]: # ()
[//]: # (```python)

[//]: # (# Compare smoothness across conditions)

[//]: # (conditions = ['baseline', 'fatigue', 'recovery'])

[//]: # (smoothness_data = {})

[//]: # ()
[//]: # (for condition in conditions:)

[//]: # (    data = load_condition_data&#40;condition&#41;)

[//]: # (    metrics = smoothness&#40;data&#41;)

[//]: # (    smoothness_data[condition] = metrics['sparc'])

[//]: # ()
[//]: # (# Lower SPARC values indicate smoother movement)

[//]: # (print&#40;f"Smoothest condition: {min&#40;smoothness_data, key=smoothness_data.get&#41;}"&#41;)

[//]: # (```)

## References

[^1]: TODO