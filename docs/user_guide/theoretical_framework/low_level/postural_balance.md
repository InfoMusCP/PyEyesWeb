# Equilibrium Analysis Module

The **Equilibrium** module quantifies balance control by evaluating the barycenter position relative to an elliptical
region defined by the two feet.

The metric produces a normalized **equilibrium value** in \([0, 1]\) indicating whether the barycenter lies within the
ellipse, and the **ellipse orientation angle** in degrees.

<span style="color:#d32f2f; font-weight:bold;">
This metric has been used for... **ADD PAPERS**  
</span>

---

## Algorithm Details

### Ellipse Construction

1. **Inputs**: 
    - Left foot position \( p_s = (x_s, y_s) \)
    - Right foot position \( p_d = (x_d, y_d) \)
    - Barycenter \( b = (x_b, y_b) \)
    - Margin \( m \) (mm)
    - Y-axis weight \( w_y \)

2. **Bounding box with margin**:

$$
\text{min} = \min(p_s, p_d) - m, \quad
\text{max} = \max(p_s, p_d) + m
$$

<ol start="3">
<li>
<strong>Ellipse center</strong>:
</li>
</ol>

$$
c = \frac{\text{min} + \text{max}}{2}
$$

<ol start="4">
<li>
<strong>Ellipse Semi-axes</strong>:  
</li>
</ol>

$$
a = \frac{\text{max}_x - \text{min}_x}{2}, \quad
b = \frac{\text{max}_y - \text{min}_y}{2} \cdot w_y
$$

<ol start="5">
<li>
<strong>Ellipse orientation</strong>  
</li>
</ol>

$$
\theta = \arctan2(y_d - y_s, \; x_d - x_s)
$$


!!! tip "Interpretation"
    The angle \( \theta \) aligns the ellipse relative to the X-axis (the line connecting the feet).

### Normalized Value Computation

1.**Relative position**:
Rotate barycenter into ellipse-aligned coordinates

$$
r = R(-\theta) \cdot (b - c)
$$

with rotation matrix

$$
R(-\theta) =
\begin{bmatrix}
\cos(-\theta) & -\sin(-\theta) \\
\sin(-\theta) & \cos(-\theta)
\end{bmatrix}
$$

<ol start="2">
<li>
<strong>Normalization</strong>  
</li>
</ol>

$$
\text{norm} = \left(\frac{r_x}{a}\right)^2 + \left(\frac{r_y}{b}\right)^2
$$

<ol start="3">
<li>
<strong>Equilibrium value</strong>  
</li>
</ol>

$$
\text{value} =
\begin{cases}
1 - \sqrt{\text{norm}}, & \text{if } \text{norm} \leq 1 \\
0, & \text{otherwise}
\end{cases}
$$


!!! tip "Interpretation"
    - **Value = 1**: barycenter at ellipse center (optimal balance).  
    - **Value = 0**: barycenter outside ellipse (loss of balance).  
    - Values in between indicate proximity to the center.

---

## Usage Examples

### Basic Equilibrium Evaluation

```python
import numpy as np
from pyeyesweb.low_level import Equilibrium

# Initialize analyzer
eq = Equilibrium(margin_mm=120, y_weight=0.6)

# Define foot positions and barycenter
left = np.array([0, 0, 0])
right = np.array([400, 0, 0])
barycenter = np.array([200, 50, 0])

value, angle = eq(left, right, barycenter)

print(f"Equilibrium value: {value:.2f}")
print(f"Ellipse angle: {angle:.1f}°")
```