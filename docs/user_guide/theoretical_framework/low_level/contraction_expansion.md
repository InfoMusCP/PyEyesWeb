# Contraction-Expansion Analysis Module

## Overview
The Contraction-Expansion module provides three distinct low-level metrics for quantifying the spatial spread of body configurations in 3D (or 2D) space:

1. **Bounding Box Filled Area**
2. **Ellipsoid Sphericity**
3. **Points Density**

These shape metrics are used to track structural changes relative to a movement baseline—for example, distinguishing a tightly curled posture from a sprawling, open posture.

## 1. Bounding Box Filled Area

### Theoretical Interpretation
- **Input Requirements**: A static frame of points in space.
- **Value Interpretation**: This computes the "Contraction Index" based on surface area compactness. A value closer to `1.0` typically indicates the posture fully occupies its volumetric bounds (highly expanded and flush), whereas smaller values indicate a tightly clustered or irregular shape relative to its global bounds.
- **Robustness**: Relies on Convex Hull computation which gracefully handles outlier limbs but can fail mathematically if all points form a flat plane (degeneracy). 

### Algorithm Details & Mathematics
The index is the ratio of the squared surface area of the enclosed convex hull to the surface area of the axis-aligned bounding box (AABB).

$$ 
Index = \frac{Area_{hull}^2}{Area_{bbox}}
$$

where $Area_{hull}$ is the internal surface area derived purely from the outermost perimeter of points, and $Area_{bbox}$ is the theoretical bounding rectangle/prism containing all movement.

## 2. Ellipsoid Sphericity

### Theoretical Interpretation
- **Input Requirements**: A static frame of spatial coordinates.
- **Value Interpretation**: Sphericity quantifies how closely the current body posture resembles a perfect sphere versus an elongated line or flat disc. A perfectly spherical posture yields `1.0`, while a highly stretched limb posture approaches `0.0`.

!!! tip "Rotational Invariance"
    Because this metric relies on Principal Component Analysis (PCA) to find the primary axes, it is highly robust against the subject's rotation in space.

### Algorithm Details & Mathematics
The algorithm fits a 3D ellipsoid to the skeletal joints using PCA on the mean-centered point cloud. The sorted eigenvalues yield the primary radii $(a, b, c)$ where $a$ is the major axis and $c$ is the minor axis.

Sphericity $S$ is defined as the ratio of the smallest to the largest radius:

$$
S = \frac{c}{a}
$$

where $c$ is the length of the shortest semi-axis and $a$ is the length of the longest semi-axis of the fitted ellipsoid.

## 3. Points Density

### Theoretical Interpretation
- **Input Requirements**: A static snippet of spatial coordinates.
- **Value Interpretation**: Evaluates the dispersion of the body. Smaller values mean all points are tightly clustered near the center of mass (high density / contracted). Larger values indicate the body is widely spread out (low density / expanded).

### Algorithm Details & Mathematics
Computes the average Euclidean distance of all points from their shared barycenter.

$$
D = \frac{1}{N} \sum_{i=1}^{N} \| X_i - \bar{X} \|
$$

where $N$ is the total number of points, $X_i$ is the position of the $i$-th point, and $\bar{X}$ is the exact spatial mean of the point cloud.

## References

### TODO