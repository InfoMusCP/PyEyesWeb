import numpy as np

class Equilibrium:
    """
    Elliptical equilibrium evaluation between two feet and a barycenter.

    This class defines an elliptical region of interest (ROI) aligned with the
    line connecting the left and right foot. The ellipse is scaled by a margin
    in millimeters and can be weighted along the Y-axis to emphasize forward–
    backward sway more than lateral sway. A barycenter is evaluated against
    this ellipse to compute a normalized equilibrium value.

    Read more in the [User Guide](/PyEyesWeb/user_guide/theoretical_framework/low_level/postural_balance/)

    Parameters
    ----------
    margin_mm : float, optional
        Extra margin in millimeters added around the rectangle spanned by the
        two feet (default: 100).
    y_weight : float, optional
        Weighting factor applied to the ellipse height along the Y-axis.
        A value < 1 shrinks the ellipse in the forward/backward direction,
        emphasizing sway in that axis (default: 0.5).

    Examples
    --------
    >>> import numpy as np
    >>> eq = Equilibrium(margin_mm=120, y_weight=0.6)

    # Using 3D coordinates
    >>> left = np.array([0, 0, 0])
    >>> right = np.array([400, 0, 0])
    >>> barycenter = np.array([200, 50, 0])
    >>> result = eq(left, right, barycenter)
    >>> round(result['value'], 2)
    0.91
    >>> round(result['angle'], 1)
    0.0

    # Using 2D coordinates (z is optional)
    >>> left_2d = np.array([0, 0])
    >>> right_2d = np.array([400, 0])
    >>> barycenter_2d = np.array([200, 50])
    >>> result_2d = eq(left_2d, right_2d, barycenter_2d)
    >>> round(result_2d['value'], 2)
    0.91
    >>> round(result_2d['angle'], 1)
    0.0
    """

    def __init__(self, margin_mm=100, y_weight=0.5):
        self.margin = margin_mm
        self.y_weight = y_weight

    def __call__(self, left_foot: np.ndarray, right_foot: np.ndarray, barycenter: np.ndarray) -> dict:
        """
        Evaluate the equilibrium value and ellipse angle.

        Parameters
        ----------
        left_foot : numpy.ndarray, shape (2,) or (3,)
            2D coordinates (x, y) or 3D coordinates (x, y, z) of the left foot in millimeters.
            Only the x and y components are used.
        right_foot : numpy.ndarray, shape (2,) or (3,)
            2D coordinates (x, y) or 3D coordinates (x, y, z) of the right foot in millimeters.
            Only the x and y components are used.
        barycenter : numpy.ndarray, shape (2,) or (3,)
            2D coordinates (x, y) or 3D coordinates (x, y, z) of the barycenter in millimeters.
            Only the x and y components are used.

        Returns
        -------
        dict
            Dictionary containing:
            - 'value': Equilibrium value in [0, 1].
                      1 means the barycenter is perfectly at the ellipse center.
                      0 means the barycenter is outside the ellipse.
            - 'angle': Orientation of the ellipse in degrees, measured counter-clockwise
                      from the X-axis (line connecting left and right foot).

        Notes
        -----
        - The ellipse is aligned with the line connecting the two feet.
        - The ellipse width corresponds to the horizontal foot span + margin.
        - The ellipse height corresponds to the vertical span + margin,
          scaled by `y_weight`.
        - If 3D coordinates are provided, the z component is ignored.
        """
        # Convert to numpy arrays and extract x,y components
        # Works for both 2D (x,y) and 3D (x,y,z) inputs
        ps = np.atleast_1d(left_foot).flatten()[:2]
        pd = np.atleast_1d(right_foot).flatten()[:2]
        bc = np.atleast_1d(barycenter).flatten()[:2]

        min_xy = np.minimum(ps, pd) - self.margin
        max_xy = np.maximum(ps, pd) + self.margin

        center = (min_xy + max_xy) / 2
        half_sizes = (max_xy - min_xy) / 2

        a = half_sizes[0]
        b = half_sizes[1] * self.y_weight

        dx, dy = pd - ps
        angle = np.arctan2(dy, dx)

        rel = bc - center

        rot_matrix = np.array([
            [np.cos(-angle), -np.sin(-angle)],
            [np.sin(-angle),  np.cos(-angle)]
        ])
        rel_rot = rot_matrix @ rel

        # Handle degenerate ellipse cases to avoid division by zero
        # Tolerance for considering a value as zero
        eps = 1e-10

        if a < eps and b < eps:
            # Both axes are zero - ellipse is a point
            # Check if barycenter is at that point
            if np.linalg.norm(rel) < eps:
                value = 1.0
            else:
                value = 0.0
        elif a < eps:
            # Ellipse is a vertical line segment (a=0, b>0)
            # Only Y position matters
            if abs(rel_rot[0]) > eps:
                # Barycenter is off the vertical line
                value = 0.0
            else:
                # Check position along Y axis
                norm_y = (rel_rot[1] / b) ** 2
                if norm_y <= 1.0:
                    value = 1.0 - np.sqrt(norm_y)
                else:
                    value = 0.0
        elif b < eps:
            # Ellipse is a horizontal line segment (a>0, b=0)
            # Only X position matters
            if abs(rel_rot[1]) > eps:
                # Barycenter is off the horizontal line
                value = 0.0
            else:
                # Check position along X axis
                norm_x = (rel_rot[0] / a) ** 2
                if norm_x <= 1.0:
                    value = 1.0 - np.sqrt(norm_x)
                else:
                    value = 0.0
        else:
            # Normal ellipse case
            norm = (rel_rot[0] / a) ** 2 + (rel_rot[1] / b) ** 2
            if norm <= 1.0:
                value = 1.0 - np.sqrt(norm)
            else:
                value = 0.0

        return {"value": max(0.0, value), "angle": np.degrees(angle)}
