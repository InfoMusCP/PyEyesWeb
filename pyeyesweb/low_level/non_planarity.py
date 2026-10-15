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
    output_type : {"curvature_radius", "curvature_value"}, optional
        ``"curvature_radius"`` (default): the output ``curvature_radius`` is the non-planarity, in the unit of the
        data. ``"curvature_value"``: the output ``curvature`` is its inverse, 1 / non-planarity. *(live)*
    radius : float, optional
        Size of the neighbourhood over which the local planes are fitted, in m (scaled by ``units``).
        Defaults to ``100.0``: that is 100 m, a value written for millimetres in the original, so with data in metres
        pass a radius of the size of your movement, for example ``0.1``. *(live)*
    nan_fraction : float, optional
        Parameter of the original block, passed to the core unchanged; dimensionless. Defaults to ``0.5``. *(live)*
    nan_value : float, optional
        Value that stands for NaN in the original block, in the unit of the output. Defaults to ``999.0``: that is
        999 m with ``units="m"``, a value written for millimetres in the original. *(live)*
    units : {"m", "mm"}, optional
        Unit of the position data: scales ``radius`` (given in metres) and names the unit of the output; the data
        and the output are never scaled. Defaults to ``"m"``. *(live)*

    Notes
    -----
    **Inputs.** ``process(points, *, timestamp=None)``: an ``(n, 3)`` array of points with row 0 the newest;
    ``run(paths, *, timestamps=None)`` takes a ``(T, n, 3)`` recording. The feature keeps no state.

    **Outputs.** ``curvature_radius`` (length, 0 for a planar path) or ``curvature`` (1/length), as ``output_type``
    says.

    **Statuses.** ``INVALID_INPUT`` for 2D points (the method is not implemented for them), for fewer than 2 points
    and for a non-finite point.

    The defaults ``radius=100.0`` and ``nan_value=999.0`` look like millimetres, while ``units`` defaults to ``"m"``:
    with data in metres the neighbourhood is 100 m wide unless a radius is given.

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
        radius = self._param("output_type", _trajectory.CurvatureOutputType.CURVATURE_RADIUS) ==             _trajectory.CurvatureOutputType.CURVATURE_RADIUS
        units = self._params["units"]
        return Schema(Output("curvature_radius", unit=units) if radius else Output("curvature", unit=f"1/{units}"))

    def _rejection(self, points: np.ndarray) -> str:
        return "fewer than 2 points" if points.shape[1] == 3 and len(points) < 2 else ""


__all__ = ["TrajectoryNonPlanarity", "average_curvature_3d"]
