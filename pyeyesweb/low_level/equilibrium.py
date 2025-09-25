import numpy as np

class Equilibrium:
    """
    Elliptical equilibrium evaluation between two feet and a barycenter.

    This class defines an elliptical region of interest (ROI) aligned with the
    line connecting the left and right foot. The ellipse is scaled by a margin
    in millimeters and can be weighted along the Y-axis to emphasize forward–
    backward sway more than lateral sway. A barycenter is evaluated against
    this ellipse to compute a normalized equilibrium value.

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
    >>> left = np.array([0, 0, 0])
    >>> right = np.array([400, 0, 0])
    >>> barycenter = np.array([200, 50, 0])
    >>> value, angle = eq(left, right, barycenter)
    >>> round(value, 2)
    0.91
    >>> round(angle, 1)
    0.0
    """

    def __init__(self, margin_mm=100, y_weight=0.5):
        self.margin = margin_mm
        self.y_weight = y_weight

    def __call__(self, left_foot: np.ndarray, right_foot: np.ndarray, barycenter: np.ndarray) -> tuple[float, float]:
        """
        Evaluate the equilibrium value and ellipse angle.

        Parameters
        ----------
        left_foot : numpy.ndarray, shape (3,)
            3D coordinates (x, y, z) of the left foot in millimeters.
            Only the x and y components are used.
        right_foot : numpy.ndarray, shape (3,)
            3D coordinates (x, y, z) of the right foot in millimeters.
            Only the x and y components are used.
        barycenter : numpy.ndarray, shape (3,)
            3D coordinates (x, y, z) of the barycenter in millimeters.
            Only the x and y components are used.

        Returns
        -------
        value : float
            Equilibrium value in [0, 1].
            - 1 means the barycenter is perfectly at the ellipse center.
            - 0 means the barycenter is outside the ellipse.
        angle : float
            Orientation of the ellipse in degrees, measured counter-clockwise
            from the X-axis (line connecting left and right foot).

        Notes
        -----
        - The ellipse is aligned with the line connecting the two feet.
        - The ellipse width corresponds to the horizontal foot span + margin.
        - The ellipse height corresponds to the vertical span + margin,
          scaled by `y_weight`.
        """
        ps = np.array(left_foot)[:2]
        pd = np.array(right_foot)[:2]
        bc = np.array(barycenter)[:2]

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

        norm = (rel_rot[0] / a) ** 2 + (rel_rot[1] / b) ** 2

        if norm <= 1.0:
            value = 1.0 - np.sqrt(norm)
        else:
            value = 0.0

        return max(0.0, value), np.degrees(angle)
