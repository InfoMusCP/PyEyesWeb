import numpy as np

from pyeyesweb.data_models.sliding_window import SlidingWindow

class DirectionChange:
    """
    Direction Change evaluation based on the angle between movement vectors.

    This class computes a single direction change index for a given trajectory
    segment. It samples three points from the trajectory (start, middle, end)
    to form two vectors and calculates the angle between them.

    The algorithm detects changes in direction that are approximately perpendicular
    (around 90 degrees).

    Parameters
    ----------
    epsilon : float, optional
        Tolerance factor (default: 0.5). Between 0.001 and 0.5. Defines how close the angle needs to
        be to 90 degrees (pi/2) to register a value and rescales the value with the threshold. 
        Values closer to 0 will yield to lower sensitivity, while values closer to 0.5 will give a smoother experience.

    Examples
    --------
    >>> import numpy as np
    >>> dc = DirectionChange(epsilon=0.5)
    >>> points = np.array([[0,0], [1,0], [2,0]]) # Straight line
    >>> result = dc(points)
    >>> result["value"]
    0.0
    >>> points = np.array([[0,0], [1,0], [1,1]]) # 90 degree turn
    >>> result = dc(points)["value"]
    1.0
    >>> points = np.array([[0,0], [1,0], [2,1]]) # 45 degree turn
    >>> result = dc(points)["value"]
    0.5
    >>> points = np.array([[0,0], [1,0], [0,0]]) # 180 degree turn
    >>> result = dc(points)["value"]
    0.0
    >>> dc = DirectionChange(epsilon=0.3)
    >>>> points = np.array([[0,0], [1,0], [2,0]]) # Straight line
    >>> result = dc(points)["value"]
    0.0
    >>> points = np.array([[0,0], [1,0], [1,1]]) # 90 degree turn
    >>> result = dc(points)["value"]
    1.0
    >>> points = np.array([[0,0], [1,0], [2,1]]) # 45 degree turn
    >>> result = dc(points)["value"]
    0.16666666666666667
    """

    def __init__(self, epsilon=0.5):
        self.epsilon = epsilon

    def __call__(self, positions: SlidingWindow) -> dict:
        """
        Compute the direction change value for the given trajectory segment.

        Parameters
        ----------
        positions : SlidingWindow
            Input array of shape (N, 3) or (N, 2) representing coordinates
            (x, y, z) or (x, y) over time.

        Returns
        -------
        dict
            Calculated direction change value between 0.0 and 1.0.
            Returns 0.0 if the segment is too short or vectors are too small.
        """
        pos = positions.to_array()
        if pos.ndim != 2 or pos.shape[1] < 2:
            raise Exception("Input positions must be a 2D array with at least 2 columns (x,y).")
        
        n_samples = pos.shape[0]

        if n_samples < 3:
            return {"value": np.nan}

        # Sample 3 points: start, middle, end
        p0 = pos[-1]          # End point
        p1 = pos[n_samples // 2]  # Middle point
        p2 = pos[0]           # Start point

        # Vectors L0 = p0 - p1 (second half), L1 = p1 - p2 (first half)
        L0 = p0 - p1
        L1 = p1 - p2

        # Norms
        norm0 = np.linalg.norm(L0)
        norm1 = np.linalg.norm(L1)

        # Avoid division by zero
        if norm0 < 1e-6 or norm1 < 1e-6:
            return {"value": 0.0}

        # Dot product
        dot = np.dot(L0, L1)
        
        # Cosine theta (clipped for numerical stability)
        cos_theta = np.clip(dot / (norm0 * norm1), -1.0, 1.0)
        
        # Angle in radians
        theta = np.arccos(cos_theta)
        
        # Normalization and scoring logic
        angle_norm = theta / np.pi
        a = 1.0 - angle_norm
        diff = np.abs(a - 0.5)
        
        # Apply epsilon threshold
        if diff < self.epsilon:
            return {"value": (1.0 - diff) / self.epsilon}
        
        return {"value": 0.0}
