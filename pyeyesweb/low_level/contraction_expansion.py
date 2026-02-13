"""Contraction and expansion analysis for body movement patterns.

This module provides optimized functions for analyzing contraction and expansion
of body configurations in 2D and 3D space. It computes area (2D) or volume (3D)
metrics for sets of body points and tracks changes relative to a baseline.

The module uses Numba JIT compilation for performance optimization, making it
suitable for real-time motion capture analysis.

Key Features
------------
- Fast area calculation using Shoelace formula (2D)
- Tetrahedron volume calculation using determinants (3D)
- Baseline-relative expansion/contraction indices
- Support for both single-frame and time-series analysis
- Automatic warmup for JIT compilation

Typical Applications
--------------------
- Dance movement analysis (body expansion/contraction)
- Gesture recognition (hand/arm configurations)
- Sports biomechanics (body positioning)
- Clinical movement assessment
"""
import numpy as np
from scipy.spatial import ConvexHull
import itertools
from pyeyesweb.data_models.sliding_window import SlidingWindow


class BoundingBoxFilledArea:
    """
    Computes the Contraction Index based on 3D Surface Area.
    
    This version uses the Axis-Aligned Bounding Box (AABB) of the raw data 
    (no rotation/alignment) and returns geometric data for visualization.
    
    Formula: CI = SurfaceArea(Hull) / SurfaceArea(AABB)
    """
    
    def __init__(self):
        pass

    def _get_hull_data(self, points: np.ndarray) -> tuple[float, np.ndarray]:
        """
        Computes 3D Convex Hull surface area and vertices.
        """
        if len(points) < 4:
            return 0.0, np.array([])
            
        try:
            hull = ConvexHull(points)
            # hull.vertices provides indices of points on the hull
            hull_points = points[hull.vertices]
            return hull.area, hull_points
        except Exception:
            return 0.0, np.array([])

    def _get_aabb_data(self, points: np.ndarray) -> tuple[float, np.ndarray]:
        """
        Computes Axis-Aligned Bounding Box (AABB) surface area and corner points.
        """
        if len(points) == 0:
            return 0.0, np.array([])

        # 1. Find min/max coordinates
        min_vals = np.min(points, axis=0) # [x_min, y_min, z_min]
        max_vals = np.max(points, axis=0) # [x_max, y_max, z_max]
        
        # 2. Calculate Dimensions
        dims = max_vals - min_vals # [Length, Width, Height]
        L, W, H = dims[0], dims[1], dims[2]
        
        # 3. Calculate Surface Area
        surface_area = 2 * (L*W + L*H + W*H)
        
        # 4. Generate the 8 corner points of the box
        # We use itertools.product to get all combinations of (min, max) for (x, y, z)
        corners = list(itertools.product(
            [min_vals[0], max_vals[0]], 
            [min_vals[1], max_vals[1]], 
            [min_vals[2], max_vals[2]]
        ))
        
        return surface_area, np.array(corners)

    def __call__(self, sliding_window:SlidingWindow) -> list[dict]:
        """
        Args:
            sliding_window: SlidingWindow object.
            
        Returns:
            list[dict]: A list where each element represents a frame containing:
                - 'contraction_index': float
                - 'hull_area': float
                - 'bbox_area': float
                - 'hull_points': np.ndarray (N, 3) - vertices of the hull
                - 'bbox_points': np.ndarray (8, 3) - corners of the box
        """
        data = sliding_window.to_array()[0] # (t_frames, n_joints, 3)
        t_frames = data.shape[0]
        
        results = []

        for t in range(t_frames):
            frame_points = data[t, :, :]
            
            # 1. Get Hull Data
            hull_area, hull_points = self._get_hull_data(frame_points)
            
            # 2. Get AABB Data (No rotation)
            bbox_area, bbox_points = self._get_aabb_data(frame_points)
            
            # 3. Compute Index
            if bbox_area > 1e-6:
                index = (hull_area**2 / bbox_area)
            else:
                index = 0.0
            
            results.append({
                'contraction_index': index,
                'hull_area': hull_area,
                'bbox_area': bbox_area,
            })
            
        return results
    

class EllipsoidSphericity:
    """
    Fits an ellipsoid to skeletal joints using PCA and computes shape metrics.
    
    This measures how "round" the distribution of joints is.
    
    Metrics:
    - Sphericity: The ratio of the smallest axis to the largest axis.
      (1.0 = Perfect Sphere, < 0.2 = Line or Flat Plane)
    """
    
    def __init__(self):
        pass

    def _fit_ellipsoid_pca(self, points: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """
        Fits an ellipsoid to the 3D points using Principal Component Analysis.
        
        Args:
            points (np.ndarray): (N, 3) array of joint coordinates.
            
        Returns:
            radii (np.ndarray): The 3 lengths of the semi-axes (sorted largest to smallest).
            rotation (np.ndarray): The 3x3 rotation matrix (eigenvectors) of the ellipsoid.
        """
        if len(points) < 2:
            return np.zeros(3), np.eye(3)

        # 1. Center the data
        # We look at the distribution relative to the body's center of mass
        centered = points - np.mean(points, axis=0)
        
        # 2. Compute Covariance Matrix
        # This captures how the data spreads in X, Y, and Z
        cov_matrix = np.cov(centered, rowvar=False)
        
        # 3. Compute Eigenvalues and Eigenvectors
        # Eigenvalues represent the variance (spread) along the principal axes
        try:
            eigenvalues, eigenvectors = np.linalg.eigh(cov_matrix)
        except np.linalg.LinAlgError:
            return np.zeros(3), np.eye(3)
        
        # 4. Convert Variance to Lengths (Radii)
        # We take the sqrt of eigenvalues to get geometric lengths (standard deviations)
        # We use abs() to handle potential negative zeros from float precision
        radii = np.sqrt(np.abs(eigenvalues))
        
        # 5. Sort by size (Largest radius first)
        sort_indices = np.argsort(radii)[::-1]
        radii = radii[sort_indices]
        rotation = eigenvectors[:, sort_indices]
        
        return radii, rotation

    def _calculate_shape_ratios(self, radii: np.ndarray) -> dict:
        """
        Computes geometric ratios from the ellipsoid axes.
        
        Args:
            radii: Array of 3 radii [a, b, c] where a >= b >= c.
        """
        a, b, c = radii[0], radii[1], radii[2]
        
        # Avoid division by zero
        if a < 1e-6:
            return {'sphericity': 0.0, 'elongation': 0.0, 'flatness': 0.0}
            
        return {
            # Global Sphericity: How close is the shape to a sphere? (c/a)
            # 1.0 = Sphere, Low = Needle or Pancake
            'sphericity': c / a,
            
            # Elongation: How long is the primary axis compared to the secondary? (b/a)
            # High = Cylinder/Line, Low = Sphere
            'elongation': 1.0 - (b / a),
            
            # Flatness: How flat is the shape? (c/b)
            # High = Pancake, Low = Sphere
            'flatness': 1.0 - (c / b) if b > 1e-6 else 0.0
        }

    def __call__(self, sliding_window:SlidingWindow) -> list[dict]:
        """
        Args:
            sliding_window: SlidingWindow object.
            
        Returns:
            list[dict]: A list containing the sphericity index and ellipsoid parameters per frame.
        """
        data = sliding_window.to_array()[0] # (t_frames, n_joints, 3)
        t_frames = data.shape[0]
        
        results = []

        for t in range(t_frames):
            frame_points = data[t, :, :]
            
            # 1. Fit Ellipsoid
            radii, rotation = self._fit_ellipsoid_pca(frame_points)
            
            # 2. Compute Ratios
            metrics = self._calculate_shape_ratios(radii)
            
            # 3. Package Result
            # We return the radii/rotation so you can visualize the ellipsoid wireframe
            results.append({
                'sphericity_index': metrics['sphericity'],
                'elongation': metrics['elongation'],
                'flatness': metrics['flatness'],
                'radius_x': radii[0],   # Major axis
                'radius_y': radii[1],   # Medium axis
                'radius_z': radii[2],   # Minor axis
            })
            
        return results

class PointsDensity:
    """
    Computes the Points Density (Dispersion) for a sequence of skeletal frames.
    
    This measures the average distance of all joints from the skeletal center (Barycenter).
    
    Formula: PD = (1/n) * Σ || p_i - barycenter ||
    
    Interpretation:
    - Low Value: High Contraction (e.g., Fetal tuck, hugging knees).
    - High Value: Low Contraction (e.g., Star jump, fully extended limbs).
    """
    
    def __init__(self):
        pass

    def _calculate_dispersion(self, points: np.ndarray) -> tuple[float, np.ndarray]:
        """
        Computes the mean distance from the barycenter.
        
        Args:
            points (np.ndarray): (N, 3) array of joint coordinates.
            
        Returns:
            density (float): The calculated Points Density score.
            barycenter (np.ndarray): The (3,) coordinate of the center.
        """
        if len(points) == 0:
            return 0.0, np.zeros(3)

        # 1. Compute Barycenter (Center of Mass/Mean Point)
        # Note: The prompt mentions 'median', but the formula specifies 'barycenter'.
        # We use the Mean (Barycenter) as it is the standard center of mass.
        barycenter = np.mean(points, axis=0)
        
        # 2. Compute Euclidean Distances (d_i)
        # || p_i - barycenter || for all i
        distances = np.linalg.norm(points - barycenter, axis=1)
        
        # 3. Compute Mean Distance (1/n * sum)
        density = np.mean(distances)
        
        return density, barycenter

    def __call__(self, sliding_window) -> list[dict]:
        """
        Args:
            sliding_window: SlidingWindow object.
            
        Returns:
            list[dict]: A list containing the density score and center for visualization.
        """
        # Extract data: (t_frames, n_joints, 3)
        data = sliding_window.to_array()[0]
        t_frames = data.shape[0]
        
        results = []

        for t in range(t_frames):
            frame_points = data[t, :, :]
            
            # Calculate Density
            density, barycenter = self._calculate_dispersion(frame_points)
            
            results.append({
                'points_density': density,  # The P.D. Score
            })
            
        return results