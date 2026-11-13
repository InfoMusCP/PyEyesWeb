"""Non-planarity of a trajectory: the mean distance of its points from local best-fit planes."""

import numpy as np

from pyeyesweb._core import core
from pyeyesweb.base.point_list import PointListFeature
from pyeyesweb.catalog import Layer, describe
from pyeyesweb.data_models.results import Output, Schema

_trajectory = core.trajectory

average_curvature_3d = _trajectory.average_curvature_3d


@describe(Layer.LOW_LEVEL, eyesweb="GetAverageCurvatue (Curvature3D)")
class TrajectoryNonPlanarity(PointListFeature):
    r"""Non-planarity of a 3D trajectory: the mean distance of its points from local best-fit planes.

    A movement that stays in a plane (a circle, a swing) has non-planarity 0; a movement that leaves it (a spiral, a
    twisting gesture) has a larger value. For the points of the trajectory the feature fits local best-fit planes over
    neighbourhoods of size ``radius`` and averages the distance of the points from them; the output is in the unit of
    the data. It is not a geometric curvature: for the curvature of a trajectory use
    ``Kinematics(output_type="curvature")``.

    Parameters
    ----------
    radius : float, optional
        Size of the neighbourhood over which the local planes are fitted, in m (scaled by ``units``). Defaults to
        ``0.1`` (10 cm; the original's 100 was written for millimetres). Choose it of the size of the movement: a
        neighbourhood that holds only its own point fits nothing. *(live)*
    nan_fraction : float, optional
        Largest share of the points whose local plane may be undefined; above it the result is undefined.
        Dimensionless, in [0, 1]. Defaults to ``0.5``. *(live)*
    units : {"m", "mm"}, optional
        Unit of the position data: scales ``radius`` (given in metres) and names the unit of the output; the data
        and the output are never scaled. Defaults to ``"m"``. *(live)*

    Notes
    -----
    **Inputs.** ``process(points, *, timestamp=None)``: an ``(n, 3)`` array of points with row 0 the newest;
    ``run(paths, *, timestamps=None)`` takes a ``(T, n, 3)`` recording. The feature keeps no state.

    **Outputs.** ``curvature_radius``: the non-planarity, a length in the unit of the data, 0 for a planar path.

    **Statuses.** ``INVALID_INPUT`` (no output) for 2D points (the method is not implemented for them), for fewer than
    2 points, for a non-finite point, when no point has another point within ``radius`` (nothing to fit), and when more
    than ``nan_fraction`` of the local planes are undefined.

    **Changed from EyesWeb.** The output type "Curvature Value" (1 / non-planarity) is not provided: the inverse of
    this distance has no geometric meaning. The original returned 0 when no point had a neighbour, and a marker value
    (``NaNValue``, 999) when too many planes were undefined; both are ``INVALID_INPUT`` here.

    Examples
    --------
    >>> import numpy as np
    >>> from pyeyesweb.low_level import TrajectoryNonPlanarity
    >>> angle = np.linspace(0.0, 2.0 * np.pi, 30)
    >>> circle = np.c_[np.cos(angle), np.sin(angle), np.zeros_like(angle)]  # a planar path
    >>> spiral = np.c_[np.cos(2 * angle), np.sin(2 * angle), 0.2 * angle]
    >>> feature = TrajectoryNonPlanarity(radius=1.0)
    >>> float(feature.process(circle).curvature_radius), float(feature.process(spiral).curvature_radius) > 0
    (0.0, True)
    """
    _core_class = _trajectory.TrajectoryNonPlanarity
    _unit_params = {"radius": 1}  # a length

    def _schema(self) -> Schema:
        return Schema(Output("curvature_radius", unit=self._params["units"]))

    def _rejection(self, points: np.ndarray) -> str:
        if points.shape[1] != 3:
            return ""
        if len(points) < 2:
            return "fewer than 2 points"
        radius = float(self._param("radius", 0.1)) * (1000.0 if self._params["units"] == "mm" else 1.0)
        distances = np.linalg.norm(points[:, None, :] - points[None, :, :], axis=-1)
        np.fill_diagonal(distances, np.inf)
        return "" if (distances <= radius).any() else "no point has another point within radius: nothing to fit"


__all__ = ["TrajectoryNonPlanarity", "average_curvature_3d"]
