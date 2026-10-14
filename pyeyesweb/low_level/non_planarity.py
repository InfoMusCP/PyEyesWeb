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
    """EyesWeb GetAverageCurvatue (Curvature3D), the mean distance of a trajectory from local best-fit planes.
    `process(points, *, timestamp=None)`, an `(n, D)` array of points, row 0 = newest (`run` takes `(T, n, D)`).
    One output: `curvature_radius` (CURVATURE_RADIUS, default) = the non-planarity, or `curvature` (CURVATURE_VALUE)
    = 1 / non-planarity. Non-planarity is EyesWeb's mean distance of the points from local best-fit planes (0 for
    planar paths, such as a circle), not a geometric curvature; for the curvature of a trajectory use
    `Kinematics(output_type="curvature")`.
    2D points: `INVALID_INPUT`; fewer than 2 points (EyesWeb outputs NaN for none) also."""
    _core_class = _trajectory.TrajectoryNonPlanarity
    _unit_params = {"radius": 1}  # a length

    def _schema(self) -> Schema:
        radius = self._param("output_type", _trajectory.CurvatureOutputType.CURVATURE_RADIUS) ==             _trajectory.CurvatureOutputType.CURVATURE_RADIUS
        units = self._params["units"]
        return Schema(Output("curvature_radius", unit=units) if radius else Output("curvature", unit=f"1/{units}"))

    def _rejection(self, points: np.ndarray) -> str:
        return "fewer than 2 points" if points.shape[1] == 3 and len(points) < 2 else ""


__all__ = ["TrajectoryNonPlanarity", "average_curvature_3d"]
