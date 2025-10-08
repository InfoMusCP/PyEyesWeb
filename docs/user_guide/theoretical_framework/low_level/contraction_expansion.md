# Contraction-Expansion Analysis Module

The Contraction-Expansion module quantifies spatial dynamics of movement patterns by analyzing how trajectories expand and contract in space over time.

Spatial movement analysis examines how body segments or markers change their relative positions during movement.
The module provides:

- **2D/3D area calculations**: geometric area enclosed by trajectory points
- **Volume analysis**: 3D spatial volume changes
- **Expansion-contraction rates**: temporal derivatives of spatial measures


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

[//]: # (## Usage Examples)

[//]: # ()
[//]: # (### Basic Area Analysis)

[//]: # ()
[//]: # (```python)

[//]: # (import numpy as np)

[//]: # (from pyeyesweb.low_level.contraction_expansion import _area_2d_fast)

[//]: # ()
[//]: # (# Define four corner points of a movement trajectory)

[//]: # (trajectory_points = np.array&#40;[)

[//]: # (    [0.0, 0.0],  # Point 1)

[//]: # (    [1.0, 0.0],  # Point 2)

[//]: # (    [1.0, 1.0],  # Point 3)

[//]: # (    [0.0, 1.0]  # Point 4)

[//]: # (]&#41;)

[//]: # ()
[//]: # (area = _area_2d_fast&#40;trajectory_points&#41;)

[//]: # (print&#40;f"Enclosed area: {area:.3f}"&#41;)

[//]: # (```)

[//]: # ()
[//]: # (### Real-Time Expansion Analysis)

[//]: # ()
[//]: # (```python)

[//]: # (from collections import deque)

[//]: # (import numpy as np)

[//]: # ()
[//]: # (class MovementExpansionTracker:)

[//]: # (    def __init__&#40;self, history_length=10&#41;:)

[//]: # (        self.area_history = deque&#40;maxlen=history_length&#41;)

[//]: # (        )
[//]: # (    def update_movement&#40;self, corner_points&#41;:)

[//]: # (        current_area = _area_2d_fast&#40;corner_points&#41;)

[//]: # (        self.area_history.append&#40;current_area&#41;)

[//]: # (        )
[//]: # (        if len&#40;self.area_history&#41; >= 2:)

[//]: # (            expansion_rate = &#40;)

[//]: # (                self.area_history[-1] - self.area_history[-2])

[//]: # (            &#41;)

[//]: # (            return {)

[//]: # (                'current_area': current_area,)

[//]: # (                'expansion_rate': expansion_rate,)

[//]: # (                'is_expanding': expansion_rate > 0)

[//]: # (            })

[//]: # (        return {'current_area': current_area})

[//]: # ()
[//]: # (# Usage)

[//]: # (tracker = MovementExpansionTracker&#40;&#41;)

[//]: # ()
[//]: # (for frame in motion_data:)

[//]: # (    # Extract four key points from current frame)

[//]: # (    corners = extract_movement_corners&#40;frame&#41;)

[//]: # (    metrics = tracker.update_movement&#40;corners&#41;)

[//]: # (    )
[//]: # (    if 'expansion_rate' in metrics:)

[//]: # (        if metrics['is_expanding']:)

[//]: # (            print&#40;f"Movement expanding at rate: {metrics['expansion_rate']:.3f}"&#41;)

[//]: # (        else:)

[//]: # (            print&#40;f"Movement contracting at rate: {metrics['expansion_rate']:.3f}"&#41;)

[//]: # (```)

[//]: # ()
[//]: # (### 3D Movement Analysis)

[//]: # ()
[//]: # (```python)

[//]: # (from pyeyesweb.low_level.contraction_expansion import _volume_3d_fast)

[//]: # ()
[//]: # ()
[//]: # (# Analyze 3D movement volume changes)

[//]: # (def analyze_3d_movement_volume&#40;trajectory_data&#41;:)

[//]: # (    volume_timeline = [])

[//]: # ()
[//]: # (    for frame in trajectory_data:)

[//]: # (        # Extract key 3D points)

[//]: # (        key_points = extract_key_3d_points&#40;frame&#41;)

[//]: # ()
[//]: # (        if len&#40;key_points&#41; >= 4:  # Minimum for volume calculation)

[//]: # (            volume = _volume_3d_fast&#40;key_points&#41;)

[//]: # (            volume_timeline.append&#40;volume&#41;)

[//]: # ()
[//]: # (    # Calculate expansion/contraction phases)

[//]: # (    expansion_phases = [])

[//]: # (    for i in range&#40;1, len&#40;volume_timeline&#41;&#41;:)

[//]: # (        if volume_timeline[i] > volume_timeline[i - 1]:)

[//]: # (            expansion_phases.append&#40;i&#41;)

[//]: # ()
[//]: # (    return {)

[//]: # (        'volume_timeline': volume_timeline,)

[//]: # (        'expansion_frames': expansion_phases,)

[//]: # (        'max_volume': max&#40;volume_timeline&#41;,)

[//]: # (        'min_volume': min&#40;volume_timeline&#41;)

[//]: # (    })

[//]: # (```)

[//]: # ()
[//]: # (### Integration with Other Modules)

[//]: # (Consider combining with **other metrics** for a more comprehensive analysis.  )

[//]: # ()
[//]: # (#### Smoothness Analysis)

[//]: # (Combine spatial dynamics with movement smoothness:)

[//]: # ()
[//]: # (```python)

[//]: # (from pyeyesweb import Smoothness)

[//]: # (from pyeyesweb.low_level.contraction_expansion import _area_2d_fast)

[//]: # ()
[//]: # (smoothness_analyzer = Smoothness&#40;&#41;)

[//]: # (spatial_areas = [])

[//]: # ()
[//]: # (for frame in motion_data:)

[//]: # (    # Calculate spatial measure)

[//]: # (    area = _area_2d_fast&#40;extract_corners&#40;frame&#41;&#41;)

[//]: # (    spatial_areas.append&#40;area&#41;)

[//]: # ()
[//]: # (    # Analyze spatial smoothness)

[//]: # (    if len&#40;spatial_areas&#41; >= smoothness_analyzer.min_length:)

[//]: # (        spatial_smoothness = smoothness_analyzer&#40;spatial_areas&#41;)

[//]: # (```)

[//]: # ()
[//]: # (#### Bilateral Symmetry)

[//]: # (Compare left-right spatial patterns:)

[//]: # ()
[//]: # (```python)

[//]: # (left_areas = [_area_2d_fast&#40;left_points[i]&#41; for i in frames])

[//]: # (right_areas = [_area_2d_fast&#40;right_points[i]&#41; for i in frames])

[//]: # ()
[//]: # (symmetry_analyzer = BilateralSymmetryAnalyzer&#40;&#41;)

[//]: # (spatial_symmetry = symmetry_analyzer.calculate_symmetry_index&#40;)

[//]: # (    left_areas, right_areas)

[//]: # (&#41;)

[//]: # (```)

[//]: # ()
[//]: # (---)

!!! warning "Limitations & Considerations"
    - Assumes meaningful geometric shapes from selected points.  
    - Requires consistent **point topology** across frames.  
    - May not capture the **full spatial complexity** of movement.
    - Performance depends on **point selection strategy**.
    - Always consider the **movement context** when interpreting results.  
    - Normalize for **subject/task differences** when appropriate.  

## References

[^1]: TODO