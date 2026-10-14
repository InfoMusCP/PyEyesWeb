"""Shape of contours and point clouds: curvature, convex hull, body parts from curvature.

A contour is one frame of `(x, y)` points, an `(N, 2)` array. Every feature declares its outputs as a `Schema` (`feature.outputs`) and returns a
`Result` (see `pyeyesweb.data_models`).
"""

from typing import Any, Optional

import numpy as np

from pyeyesweb.physical_signals._contour import CONTOUR, ContourFeature
from pyeyesweb._core import core
from pyeyesweb.base.core_feature import XY, CoreFeature
from pyeyesweb.catalog import Layer, describe
from pyeyesweb.data_models.inputs import Input, InputKind, Inputs
from pyeyesweb.data_models.results import Output, Result, Schema

_motion = core.motion


@describe(Layer.LOW_LEVEL, eyesweb="contourstolist (CurvatureFunction)")
class ContourCurvature(ContourFeature):
    """EyesWeb CurvatureFunction. `process(contour, *, timestamp=None)`, `contour` an `(N, 2)` array (`run` takes `(T, N, 2)`).

    Output `curvature`: one value per contour point (1 / length units), data-dependent size. Always `OK`.
    """
    _core_class = _motion.ContourCurvature

    def _schema(self) -> Schema:
        return Schema(Output("curvature", (None,), doc="curvature per contour point"))

    def _to_result(self, raw: np.ndarray, timestamp: float) -> Result:
        return self.result(timestamp=timestamp, curvature=raw)


@describe(Layer.LOW_LEVEL, eyesweb="body_parts_from_curvature")
class BodyPartsFromCurvature(CoreFeature):
    """EyesWeb BodyPartsFromCurvature. `process(curvature, contour, *, timestamp=None)`: the `(N,)` curvature of each point
    of the `(N, 2)` contour (`run(curvatures, contours)` takes `(T, N)` and `(T, N, 2)`).

    Outputs `minimums` and `maximums`: contour points at the curvature extrema, labelled outputs
    `label -> (x, y)`. Always `OK`.
    """
    _core_class = _motion.BodyPartsFromCurvature
    _core_names = {"number_of_points": "points_number"}
    INPUTS = Inputs(Input("curvature", InputKind.SAMPLE, (None,), doc="curvature of each contour point"), CONTOUR)

    def _schema(self) -> Schema:
        return Schema(Output("minimums", components=XY, labelled=True, doc="points at curvature minima"),
                      Output("maximums", components=XY, labelled=True, doc="points at curvature maxima"))

    def process(self, curvature: Any, contour: Any, *, timestamp: Optional[float] = None) -> Result:
        if len(np.atleast_1d(curvature)) != len(contour) and len(contour) and np.size(curvature):
            raise ValueError(f"BodyPartsFromCurvature: curvature holds {len(np.atleast_1d(curvature))} values but "
                             f"contour {len(contour)} points: one curvature per contour point")
        return self._to_result(self._block.process(curvature, contour), timestamp)

    def _to_result(self, raw: Any, timestamp: Optional[float]) -> Result:
        minimums, maximums = raw
        return self.result(timestamp=timestamp, minimums=minimums, maximums=maximums)


@describe(Layer.LOW_LEVEL, eyesweb="ConvexHull")
class ConvexHull(ContourFeature):
    """EyesWeb ConvexHull. `process(contour, *, timestamp=None)`, `contour` an `(N, 2)` array (`run` takes `(T, N, 2)`).

    Output `hull`: `(H, 2)` hull vertices (components x, y), strictly convex vertices only, clockwise with y
    pointing up (counter-clockwise on screen in image coordinates), starting from the minimum-x (then minimum-y)
    point. The hull is that of the exact input coordinates.
    `INVALID_INPUT` for an empty contour.
    """
    _core_class = _motion.ConvexHull

    def _schema(self) -> Schema:
        return Schema(Output("hull", (None, 2), components=XY, doc="convex hull vertices"))

    def _to_result(self, raw: np.ndarray, timestamp: float) -> Result:
        return self.result(timestamp=timestamp, hull=raw)


__all__ = ["ContourCurvature", "ConvexHull", "BodyPartsFromCurvature"]
