"""Directness of a path (EyesWeb GetTrajectoryFeatures)."""

from pyeyesweb._core import core
from pyeyesweb.base.point_list import PointListFeature
from pyeyesweb.catalog import Layer, describe
from pyeyesweb.data_models.results import Output, Schema

_trajectory = core.trajectory


@describe(Layer.MID_LEVEL, eyesweb="GetTrajectoryFeatures (TrajectoryBasicFeatures)")
class Directness(PointListFeature):
    """Directness index of a path: straight-line distance / path length (1 = a straight line), EyesWeb
    GetTrajectoryFeatures. `process(points, *, timestamp=None)`, an `(n, D)` array of points (D = 2 or 3), row 0 = newest
    (`run` takes `(T, n, D)`). One output: `directness_index`.
    `WARMING_UP` for fewer than 2 points, `INVALID_INPUT` for a zero length."""
    _core_class = _trajectory.Directness

    def _schema(self) -> Schema:
        return Schema(Output("directness_index"))

    def _warming_up(self, points) -> str:
        return "The trajectory has just one point." if len(points) <= 1 else ""


__all__ = ["Directness"]
