import numpy as np
from numba import jit


@jit(nopython=True, cache=True)
def _area_2d_fast(points):
    """I think this is an ultra-fast 2D area calculation using Shoelace formula."""
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
    """Here we use an optimized determinant."""
    v1x, v1y, v1z = points[1, 0] - points[0, 0], points[1, 1] - points[0, 1], points[1, 2] - points[0, 2]
    v2x, v2y, v2z = points[2, 0] - points[0, 0], points[2, 1] - points[0, 1], points[2, 2] - points[0, 2]
    v3x, v3y, v3z = points[3, 0] - points[0, 0], points[3, 1] - points[0, 1], points[3, 2] - points[0, 2]
    
    det = v1x * (v2y * v3z - v2z * v3y) - v1y * (v2x * v3z - v2z * v3x) + v1z * (v2x * v3y - v2y * v3x)
    
    return abs(det) / 6.0


@jit(nopython=True, cache=True)
def _analyze_frame_2d(points, baseline_metric):
    """Optimized single frame analysis for 2D."""
    metric = _area_2d_fast(points)
    
    if baseline_metric <= 0:
        index = 1.0 if metric == 0 else np.inf
        state = 0  # neutral
    else:
        index = metric / baseline_metric
        if metric > baseline_metric:
            state = 1  # expansion
        elif metric < baseline_metric:
            state = -1  # contraction
        else:
            state = 0  # neutral
    
    return metric, index, state


@jit(nopython=True, cache=True)
def _analyze_frame_3d(points, baseline_metric):
    """Optimized single frame analysis for 3D."""
    metric = _volume_3d_fast(points)
    
    if baseline_metric <= 0:
        index = 1.0 if metric == 0 else np.inf
        state = 0  # neutral
    else:
        index = metric / baseline_metric
        if metric > baseline_metric:
            state = 1  # expansion
        elif metric < baseline_metric:
            state = -1  # contraction
        else:
            state = 0  # neutral
    
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
    """Here we use a vectorized timeseries processing for 3D."""
    n_frames = data.shape[0]
    baseline_metric = _volume_3d_fast(data[baseline_frame])
    
    metrics = np.empty(n_frames, dtype=np.float64)
    indices = np.empty(n_frames, dtype=np.float64)
    states = np.empty(n_frames, dtype=np.int8)
    
    for i in range(n_frames):
        metrics[i], indices[i], states[i] = _analyze_frame_3d(data[i], baseline_metric)
    
    return metrics, indices, states


def analyze_movement(data, mode=None, baseline_frame=0):
    """
    Analyze body movement contraction/expansion patterns.
    
    Args:
        data: numpy array (n_frames, 4, 2/3) or (4, 2/3)
        mode: "2D", "3D", or None for auto-detection  
        baseline_frame: baseline frame index for timeseries
        
    Returns:
        dict: Single frame result or timeseries results
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


# This module is just a warmup JIT compilation
def _warmup():
    dummy_2d = np.array([[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]], dtype=np.float64)
    dummy_3d = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]], dtype=np.float64)
    
    _area_2d_fast(dummy_2d)
    _volume_3d_fast(dummy_3d)
    _analyze_frame_2d(dummy_2d, 1.0)
    _analyze_frame_3d(dummy_3d, 1.0)

_warmup()