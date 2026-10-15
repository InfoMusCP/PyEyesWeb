"""Directness of a path: straight-line distance over path length."""

from pyeyesweb._core import core
from pyeyesweb.base.point_list import PointListFeature
from pyeyesweb.catalog import Layer, describe
from pyeyesweb.data_models.results import Output, Schema

_trajectory = core.trajectory


@describe(Layer.LOW_LEVEL, eyesweb="GetTrajectoryFeatures (TrajectoryBasicFeatures)")
class Directness(PointListFeature):
    r"""Directness index of a path: straight-line distance over path length, 1 for a straight line.

    Directness tells whether a point went straight to where it ended up or wandered. For a path of :math:`n` points
    :math:`\mathbf{p}_1, \dots, \mathbf{p}_n` (from the oldest to the newest),

    .. math::

        D = \frac{\lVert \mathbf{p}_n - \mathbf{p}_1 \rVert}{\sum_{i=1}^{n-1} \lVert \mathbf{p}_{i+1} - \mathbf{p}_i \rVert}
        \in [0, 1],

    that is 1 for a straight path and tends to 0 for a path that returns to its start.

    Notes
    -----
    **Inputs.** ``process(points, *, timestamp=None)``: an ``(n, D)`` array of points, ``D`` = 2 or 3, with row 0 the
    newest point (any unit of length); ``run(paths, *, timestamps=None)`` takes a ``(T, n, D)`` recording. The feature
    keeps no state; the path is the one given at each call.

    **Outputs.** ``directness_index`` (dimensionless, in [0, 1]).

    **Statuses.** ``WARMING_UP`` for fewer than 2 points; ``INVALID_INPUT`` for a path of zero length, a non-finite
    point or an array of another shape.

    Examples
    --------
    >>> import numpy as np
    >>> from pyeyesweb.low_level import Directness
    >>> path = np.array([[1.0, 0.0], [0.0, 1.0], [0.0, 0.0]])  # row 0 is the newest point
    >>> round(float(Directness().process(path).directness_index), 3)
    0.414
    """
    _core_class = _trajectory.Directness

    def _schema(self) -> Schema:
        return Schema(Output("directness_index"))

    def _warming_up(self, points) -> str:
        return "The trajectory has just one point." if len(points) <= 1 else ""


__all__ = ["Directness"]
