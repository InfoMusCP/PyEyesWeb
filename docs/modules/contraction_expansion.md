# Contraction/Expansion Analysis Module

The Contraction/Expansion module quantifies spatial dynamics of movement patterns by analyzing how trajectories expand and contract in space over time. This analysis reveals movement strategies and spatial control patterns.

## Overview

Spatial movement analysis examines how body segments or markers change their relative positions during movement. The module provides:

- **2D/3D area calculations**: Geometric area enclosed by trajectory points
- **Volume analysis**: 3D spatial volume changes
- **Expansion/contraction rates**: Temporal derivatives of spatial measures
- **Real-time processing**: Numba-optimized computations for efficiency

## Key Functions

### `_area_2d_fast(points)`

Computes 2D area using the Shoelace formula with Numba optimization.

**Parameters:**
- `points` (ndarray): Array of 2D coordinates, shape (4, 2)

**Returns:**
- `float`: Area enclosed by the four points

**Algorithm:**
Uses the Shoelace formula for polygon area calculation:
```
Area = 0.5 * |Σ(x_i * y_{i+1} - x_{i+1} * y_i)|
```

### `_volume_3d_fast(points)`

Calculates 3D volume using tetrahedron volume computation.

**Parameters:**
- `points` (ndarray): Array of 3D coordinates

**Returns:**
- `float`: Volume of the 3D shape

**Algorithm:**
Decomposes 3D shapes into tetrahedra and sums volumes using cross products.

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

## Performance Optimization

### Numba JIT Compilation

The module uses Numba's Just-In-Time compilation for performance:

```python
@jit(nopython=True, cache=True)
def _area_2d_fast(points):
    # Ultra-fast computation with compiled code
    pass
```

**Benefits:**
- 10-100x speedup over pure Python
- Compiled once, cached for subsequent calls
- No Python overhead in critical loops

### Memory Efficiency

Optimizations for real-time processing:
- In-place calculations where possible
- Minimal memory allocation
- Efficient array operations

## Algorithm Details

### Shoelace Formula (2D Area)

For a quadrilateral with vertices (x₁,y₁), (x₂,y₂), (x₃,y₃), (x₄,y₄):

```
Area = 0.5 * |x₁(y₂-y₄) + x₂(y₃-y₁) + x₃(y₄-y₂) + x₄(y₁-y₃)|
```

Implemented with optimized indexing for maximum performance.

### 3D Volume Calculation

Uses tetrahedron decomposition:
1. Divide 3D shape into tetrahedra
2. Calculate each tetrahedron volume using scalar triple product
3. Sum volumes with appropriate signs

## Research Applications

### Motor Control Analysis
- Reaching movement envelope analysis
- Grasping aperture dynamics
- Multi-joint coordination patterns

### Rehabilitation Assessment
- Range of motion quantification
- Movement efficiency metrics
- Progress tracking through spatial measures

### Sports Biomechanics
- Technique analysis through spatial patterns
- Performance optimization via movement efficiency
- Injury prevention through movement quality assessment

## Parameter Considerations

### Point Selection
- Choose anatomically or functionally relevant points
- Maintain consistent point ordering across frames
- Ensure points form meaningful geometric shapes

### Temporal Resolution
- Higher sampling rates improve expansion rate accuracy
- Consider smoothing for noisy data
- Balance temporal resolution with computational efficiency

### Coordinate System
- Maintain consistent coordinate systems
- Consider normalization for cross-subject comparisons
- Account for measurement units in interpretation

## Integration with Other Modules

### Smoothness Analysis
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

### Bilateral Symmetry
Compare left-right spatial patterns:

```python
left_areas = [_area_2d_fast(left_points[i]) for i in frames]
right_areas = [_area_2d_fast(right_points[i]) for i in frames]

symmetry_analyzer = BilateralSymmetryAnalyzer()
spatial_symmetry = symmetry_analyzer.calculate_symmetry_index(
    left_areas, right_areas
)
```

## Limitations and Considerations

### Geometric Assumptions
- Assumes meaningful geometric shapes from selected points
- Requires consistent point topology across frames
- May not capture all spatial complexity

### Computational Requirements
- Numba compilation time on first use
- Memory requirements scale with trajectory length
- Performance depends on point selection strategy

### Interpretation Guidelines
- Consider movement context when interpreting results
- Normalize for subject/task differences when appropriate
- Combine with other metrics for comprehensive analysis

## References

To be added