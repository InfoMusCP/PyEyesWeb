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
from numba import jit


@jit(nopython=True, cache=True)
def _area_2d_fast(points):
    """Calculate 2D area using the Shoelace formula.

    Parameters
    ----------
    points : ndarray of shape (4, 2)
        Four 2D points forming a quadrilateral.

    Returns
    -------
    float
        Absolute area of the quadrilateral.
    """
    x = points[:, 0]
    y = points[:, 1]
    
    return 0.5 * abs(
        x[0] * y[1] - x[1] * y[0] +
        x[1] * y[2] - x[2] * y[1] +
        x[2] * y[3] - x[3] * y[2] +
        x[3] * y[0] - x[0] * y[3]
    )


@jit(nopython=True, cache=True)
def _volume_3d_fast(points):
    """Calculate 3D volume of a tetrahedron using determinant method.

    Parameters
    ----------
    points : ndarray of shape (4, 3)
        Four 3D points forming a tetrahedron.

    Returns
    -------
    float
        Absolute volume of the tetrahedron.
    """
    v1x, v1y, v1z = points[1, 0] - points[0, 0], points[1, 1] - points[0, 1], points[1, 2] - points[0, 2]
    v2x, v2y, v2z = points[2, 0] - points[0, 0], points[2, 1] - points[0, 1], points[2, 2] - points[0, 2]
    v3x, v3y, v3z = points[3, 0] - points[0, 0], points[3, 1] - points[0, 1], points[3, 2] - points[0, 2]
    
    det = v1x * (v2y * v3z - v2z * v3y) - v1y * (v2x * v3z - v2z * v3x) + v1z * (v2x * v3y - v2y * v3x)
    
    return abs(det) / 6.0


@jit(nopython=True, cache=True)
def _compute_expansion_index(metric, baseline_metric):
    """Compute expansion index and state from metric values.

    Parameters
    ----------
    metric : float
        Current metric value (area or volume).
    baseline_metric : float
        Baseline metric for comparison.

    Returns
    -------
    tuple of (float, int)
        (expansion_index, state) where state is -1 (contraction),
        0 (neutral), or 1 (expansion).
    """
    if baseline_metric <= 0:
        # When baseline is zero or negative, return NaN for index
        # as expansion/contraction ratio is undefined
        if baseline_metric < 0:
            # Negative baseline is invalid
            index = np.nan
        elif metric == 0:
            # Both baseline and current are zero - no change
            index = 1.0
        else:
            # Zero baseline but non-zero current - undefined expansion
            index = np.nan
        state = 0  # neutral
    else:
        index = metric / baseline_metric
        if metric > baseline_metric:
            state = 1  # expansion
        elif metric < baseline_metric:
            state = -1  # contraction
        else:
            state = 0  # neutral

    return index, state


@jit(nopython=True, cache=True)
def _analyze_frame_2d(points, baseline_metric):
    """Analyze single 2D frame relative to baseline.

    Parameters
    ----------
    points : ndarray of shape (4, 2)
        Four 2D points to analyze.
    baseline_metric : float
        Baseline area for comparison.

    Returns
    -------
    tuple of (float, float, int)
        (area, expansion_index, state) where state is -1 (contraction),
        0 (neutral), or 1 (expansion).
    """
    metric = _area_2d_fast(points)
    index, state = _compute_expansion_index(metric, baseline_metric)
    return metric, index, state


@jit(nopython=True, cache=True)
def _analyze_frame_3d(points, baseline_metric):
    """Analyze single 3D frame relative to baseline.

    Parameters
    ----------
    points : ndarray of shape (4, 3)
        Four 3D points to analyze.
    baseline_metric : float
        Baseline volume for comparison.

    Returns
    -------
    tuple of (float, float, int)
        (volume, expansion_index, state) where state is -1 (contraction),
        0 (neutral), or 1 (expansion).
    """
    metric = _volume_3d_fast(points)
    index, state = _compute_expansion_index(metric, baseline_metric)
    return metric, index, state


@jit(nopython=True, cache=True)
def _process_timeseries_2d(data, baseline_frame):
    """Vectorized timeseries processing for 2D."""
    n_frames = data.shape[0]
    baseline_metric = _area_2d_fast(data[baseline_frame])
    
    metrics = np.empty(n_frames, dtype=np.float64)
    indices = np.empty(n_frames, dtype=np.float64)
    states = np.empty(n_frames, dtype=np.int8)
    
    for i in range(n_frames):
        metrics[i], indices[i], states[i] = _analyze_frame_2d(data[i], baseline_metric)
    
    return metrics, indices, states


@jit(nopython=True, cache=True)
def _process_timeseries_3d(data, baseline_frame):
    """Process time series of 3D configurations.

    Parameters
    ----------
    data : ndarray of shape (n_frames, 4, 3)
        Time series of tetrahedron configurations.
    baseline_frame : int
        Frame index to use as baseline.

    Returns
    -------
    tuple of (ndarray, ndarray, ndarray)
        (volumes, expansion_indices, states) for all frames.
    """
    n_frames = data.shape[0]
    baseline_metric = _volume_3d_fast(data[baseline_frame])
    
    metrics = np.empty(n_frames, dtype=np.float64)
    indices = np.empty(n_frames, dtype=np.float64)
    states = np.empty(n_frames, dtype=np.int8)
    
    for i in range(n_frames):
        metrics[i], indices[i], states[i] = _analyze_frame_3d(data[i], baseline_metric)
    
    return metrics, indices, states


class ContractionExpansion:
    """Analyze body movement contraction/expansion patterns.

    This class provides a standardized API for computing area (2D) or volume (3D)
    metrics for body point configurations and tracking expansion/contraction
    relative to a baseline.

    Parameters
    ----------
    mode : {"2D", "3D", None}, optional
        Analysis mode. If None, auto-detects from data dimensions.
    baseline_frame : int, optional
        Frame index to use as baseline for time series (default: 0).

    Examples
    --------
    >>> # Create analyzer
    >>> ce = ContractionExpansion(mode="2D")
    >>>
    >>> # Single frame analysis
    >>> points_2d = np.array([[0, 0], [1, 0], [1, 1], [0, 1]])
    >>> result = ce(points_2d)
    >>> print(result['metric'])  # Area of square
    1.0

    >>> # Time series analysis
    >>> ce_3d = ContractionExpansion(mode="3D", baseline_frame=0)
    >>> frames = np.random.randn(100, 4, 3)
    >>> result = ce_3d(frames)
    >>> print(result['states'][:10])  # First 10 frame states
    """

    def __init__(self, mode=None, baseline_frame=0):
        self.mode = mode
        self.baseline_frame = baseline_frame

    def __call__(self, data):
        """Analyze movement data using the configured settings.

        Parameters
        ----------
        data : ndarray
            Either single frame (4, 2) or (4, 3) for 2D/3D points,
            or time series (n_frames, 4, 2) or (n_frames, 4, 3).

        Returns
        -------
        dict
            For single frame:
                - 'metric': area or volume value
                - 'dimension': "2D" or "3D"
            For time series:
                - 'metrics': array of area/volume values
                - 'indices': array of expansion indices relative to baseline
                - 'states': array of states (-1=contraction, 0=neutral, 1=expansion)
                - 'dimension': "2D" or "3D"
        """
        return analyze_movement(data, mode=self.mode, baseline_frame=self.baseline_frame)


def analyze_movement(data, mode=None, baseline_frame=0):
    """Analyze body movement contraction/expansion patterns.

    This function computes area (2D) or volume (3D) metrics for body point
    configurations and tracks expansion/contraction relative to a baseline.

    Parameters
    ----------
    data : ndarray
        Either single frame (4, 2) or (4, 3) for 2D/3D points,
        or time series (n_frames, 4, 2) or (n_frames, 4, 3).
    mode : {"2D", "3D", None}, optional
        Analysis mode. If None, auto-detects from data dimensions.
    baseline_frame : int, optional
        Frame index to use as baseline for time series (default: 0).

    Returns
    -------
    dict
        For single frame:
            - 'metric': area or volume value
            - 'dimension': "2D" or "3D"
        For time series:
            - 'metrics': array of area/volume values
            - 'indices': array of expansion indices relative to baseline
            - 'states': array of states (-1=contraction, 0=neutral, 1=expansion)
            - 'dimension': "2D" or "3D"

    Raises
    ------
    ValueError
        If data shape is invalid or mode doesn't match data dimensions.

    Examples
    --------
    >>> # Single frame 2D analysis
    >>> points_2d = np.array([[0, 0], [1, 0], [1, 1], [0, 1]])
    >>> result = analyze_movement(points_2d, mode="2D")
    >>> print(result['metric'])  # Area of square
    1.0

    >>> # Time series 3D analysis
    >>> frames = np.random.randn(100, 4, 3)
    >>> result = analyze_movement(frames, mode="3D", baseline_frame=0)
    >>> print(result['states'][:10])  # First 10 frame states
    """
    if data.ndim == 2:
        dims = data.shape[1]
        is_timeseries = False
    elif data.ndim == 3:
        dims = data.shape[2]
        is_timeseries = True
        if data.shape[1] != 4:
            raise ValueError("Invalid shape: second dimension must be 4")
    else:
        raise ValueError("Invalid data dimensions")
    
    if mode is None:
        mode = "2D" if dims == 2 else "3D" if dims == 3 else None
        if mode is None:
            raise ValueError("Invalid coordinate dimensions")
    
    expected_dims = 2 if mode == "2D" else 3
    if dims != expected_dims:
        raise ValueError(f"Mode {mode} requires {expected_dims}D data")
    
    if not is_timeseries:
        if mode == "2D":
            metric = _area_2d_fast(data)
        else:
            metric = _volume_3d_fast(data)
        
        return {"metric": metric, "dimension": mode}
    
    if mode == "2D":
        metrics, indices, states = _process_timeseries_2d(data, baseline_frame)
    else:
        metrics, indices, states = _process_timeseries_3d(data, baseline_frame)
    
    return {
        "metrics": metrics,
        "indices": indices, 
        "states": states,
        "dimension": mode
    }


def _warmup():
    """Warmup JIT compilation with dummy data."""
    dummy_2d = np.array([[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]], dtype=np.float64)
    dummy_3d = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]], dtype=np.float64)
    
    _area_2d_fast(dummy_2d)
    _volume_3d_fast(dummy_3d)
    _analyze_frame_2d(dummy_2d, 1.0)
    _analyze_frame_3d(dummy_3d, 1.0)

_warmup()