# Contraction-Expansion Analysis Module

The Contraction-Expansion module quantifies spatial dynamics of movement patterns by analyzing how trajectories expand and contract in space over time.

Spatial movement analysis examines how body segments or markers change their relative positions during movement.
The module provides:

- **2D/3D area calculations**: geometric area enclosed by trajectory points
- **Volume analysis**: 3D spatial volume changes
- **Expansion-contraction rates**: temporal derivatives of spatial measures

<span style="color:#d32f2f; font-weight:bold;">
These metrics have been used for... **ADD PAPERS**
</span>
## Algorithms Details

### 2D Area computation
The 2D implementation uses the Shoelace formula [^1] for polygon area computation:

$$
A = \tfrac{1}{2} \Bigg| \sum_i \big( x_i y_{i+1} - x_{i+1} y_i \big) \Bigg|
$$

### 3D Volume computation
Calculates 3D volume using tetrahedron volume decomposition:

1. **Divide the 3D shape into tetrahedra**  
   For a polyhedron defined by vertices \( \{p_i\}_{i=0}^n \), partition it into a set of tetrahedra \(\mathcal{T} = \{ (p_0, p_{i}, p_{j}, p_{k}) \}\).

2. **Calculate each tetrahedron volume using the scalar triple product**  
   For tetrahedron with vertices \(p_0, p_1, p_2, p_3 \in \mathbb{R}^3\)  

$$
V_{\text{tetra}} = \frac{1}{6} \; \det 
\begin{bmatrix}
x_1 - x_0 & x_2 - x_0 & x_3 - x_0 \\
y_1 - y_0 & y_2 - y_0 & y_3 - y_0 \\
z_1 - z_0 & z_2 - z_0 & z_3 - z_0
\end{bmatrix}
$$

   or equivalently:

$$
V_{\text{tetra}} = \tfrac{1}{6} \, \big( (p_1 - p_0) \cdot \big( (p_2 - p_0) \times (p_3 - p_0) \big) \big)
$$

<ol start="3">
<li>
<strong>Sum volumes with appropriate signs</strong>  
<br>The total polyhedron volume is obtained as:
</li>
</ol>  

$$
V = \sum_{k} V_{\text{tetra},k}
$$

   where the sign of each \(V_{\text{tetra},k}\) depends on the orientation of the vertices.

## Performance Optimization

### Numba JIT Compilation

The module uses Numba's Just-In-Time compilation for performance.

!!! note
    Numba introduces **compilation time** on first use, but caches compiled functions for subsequent calls.  
    This approach grants 10-100x speedups over pure Python, avoiding overhead in critical loops.

```python
@jit(nopython=True, cache=True)
def _area_2d_fast(points):
    # Ultra-fast computation with compiled code
    pass
```

### Memory Efficiency

The implementation is optimized for memory efficiency by using in-place calculations, minimizing temporary arrays, and leveraging efficient array operations.

## Usage Examples

### Basic Area Analysis

```python
import numpy as np
from pyeyesweb.low_level.contraction_expansion import _area_2d_fast

# Define four corner points of a movement trajectory
trajectory_points = np.array([
    [0.0, 0.0],  # Point 1
    [1.0, 0.0],  # Point 2
    [1.0, 1.0],  # Point 3
    [0.0, 1.0]  # Point 4
])

area = _area_2d_fast(trajectory_points)
print(f"Enclosed area: {area:.3f}")
```

### Real-Time Expansion Analysis

```python
from collections import deque
import numpy as np

class MovementExpansionTracker:
    def __init__(self, history_length=10):
        self.area_history = deque(maxlen=history_length)
        
    def update_movement(self, corner_points):
        current_area = _area_2d_fast(corner_points)
        self.area_history.append(current_area)
        
        if len(self.area_history) >= 2:
            expansion_rate = (
                self.area_history[-1] - self.area_history[-2]
            )
            return {
                'current_area': current_area,
                'expansion_rate': expansion_rate,
                'is_expanding': expansion_rate > 0
            }
        return {'current_area': current_area}

# Usage
tracker = MovementExpansionTracker()

for frame in motion_data:
    # Extract four key points from current frame
    corners = extract_movement_corners(frame)
    metrics = tracker.update_movement(corners)
    
    if 'expansion_rate' in metrics:
        if metrics['is_expanding']:
            print(f"Movement expanding at rate: {metrics['expansion_rate']:.3f}")
        else:
            print(f"Movement contracting at rate: {metrics['expansion_rate']:.3f}")
```

### 3D Movement Analysis

```python
from pyeyesweb.low_level.contraction_expansion import _volume_3d_fast


# Analyze 3D movement volume changes
def analyze_3d_movement_volume(trajectory_data):
    volume_timeline = []

    for frame in trajectory_data:
        # Extract key 3D points
        key_points = extract_key_3d_points(frame)

        if len(key_points) >= 4:  # Minimum for volume calculation
            volume = _volume_3d_fast(key_points)
            volume_timeline.append(volume)

    # Calculate expansion/contraction phases
    expansion_phases = []
    for i in range(1, len(volume_timeline)):
        if volume_timeline[i] > volume_timeline[i - 1]:
            expansion_phases.append(i)

    return {
        'volume_timeline': volume_timeline,
        'expansion_frames': expansion_phases,
        'max_volume': max(volume_timeline),
        'min_volume': min(volume_timeline)
    }
```

### Integration with Other Modules
Consider combining with **other metrics** for a more comprehensive analysis.  

#### Smoothness Analysis
Combine spatial dynamics with movement smoothness:

```python
from pyeyesweb import Smoothness
from pyeyesweb.low_level.contraction_expansion import _area_2d_fast

smoothness_analyzer = Smoothness()
spatial_areas = []

for frame in motion_data:
    # Calculate spatial measure
    area = _area_2d_fast(extract_corners(frame))
    spatial_areas.append(area)

    # Analyze spatial smoothness
    if len(spatial_areas) >= smoothness_analyzer.min_length:
        spatial_smoothness = smoothness_analyzer(spatial_areas)
```

#### Bilateral Symmetry
Compare left-right spatial patterns:

```python
left_areas = [_area_2d_fast(left_points[i]) for i in frames]
right_areas = [_area_2d_fast(right_points[i]) for i in frames]

symmetry_analyzer = BilateralSymmetryAnalyzer()
spatial_symmetry = symmetry_analyzer.calculate_symmetry_index(
    left_areas, right_areas
)
```

---

!!! warning "Limitations & Considerations"
    - Assumes meaningful geometric shapes from selected points.  
    - Requires consistent **point topology** across frames.  
    - May not capture the **full spatial complexity** of movement.
    - Performance depends on **point selection strategy**.
    - Always consider the **movement context** when interpreting results.  
    - Normalize for **subject/task differences** when appropriate.  

## References

[^1]: TODO