"""Base of the features that take a list of points, one `(n, 2)` or `(n, 3)` array per call."""

from typing import Any, Optional

import numpy as np

from pyeyesweb.base.core_feature import FrameFeature
from pyeyesweb.base.inputs import non_finite, points_input
from pyeyesweb.data_models.inputs import Inputs
from pyeyesweb.data_models.results import Result, Status


class PointListFeature(FrameFeature):
    """A block taking one list of points per call: `process(points, *, timestamp=None)`.

    `points` is an `(n, 2)` or `(n, 3)` array, row 0 = newest (`run` takes `(T, n, D)`) and has exactly one output.
    Subclasses give `_schema()` and, where they need to, `_warming_up(points)` (the reason there are too few points
    for now, or `""`) and `_rejection(points)` (the reason the points are `INVALID_INPUT` for the feature, or `""`).
    Points of another shape, and a `ValueError` of the block, are `INVALID_INPUT`.
    """

    def _inputs(self) -> Inputs:
        return Inputs(points_input("points", None, "row 0 = newest point", dims=None))

    def _warming_up(self, points: np.ndarray) -> str:
        return ""

    def _rejection(self, points: np.ndarray) -> str:
        return ""

    def _process(self, points: Any, timestamp: Optional[float]) -> Result:
        points = np.asarray(points, dtype=float)
        if points.ndim != 2 or points.shape[1] not in (2, 3):
            return self._no_output(Status.INVALID_INPUT, f"points are an (n, 2) or (n, 3) array, got shape {points.shape}",
                                  timestamp)
        if reason := non_finite(points, allow_empty=True) or self._rejection(points):
            return self._no_output(Status.INVALID_INPUT, reason, timestamp)
        if reason := self._warming_up(points):
            return self._no_output(Status.WARMING_UP, reason, timestamp)
        try:
            raw = self._block.process(points)
        except ValueError as error:
            return self._no_output(Status.INVALID_INPUT, str(error), timestamp)
        (name,) = self.outputs.names
        finite = bool(np.isfinite(raw))
        return self._result(status=Status.OK if finite else Status.INVALID_INPUT,
                           reason="" if finite else "the result is not finite", timestamp=timestamp, **{name: raw})
