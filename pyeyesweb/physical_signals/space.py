"""Detection of the grid cell hit by a point (EyesWeb HitCellDetector).

A 2D space is divided into a grid of cells: `cells_along_y` rows from the y coordinate and `cells_along_x`
columns from the x coordinate. A cell is `(i, j)` = (row, column). The block declares its outputs
as a `Schema` (`block.outputs`) and returns a `Result` (see `pyeyesweb.data_models`). Parameters, defaults and the
exact behaviour are those of the C++ port, documented in the C++ headers (`core/include/ew/features/space/`). The potentials driven by the hit cells are in
`pyeyesweb.mid_level.space_occupation`.
"""

from typing import Any, Optional

import numpy as np

from pyeyesweb._core import core
from pyeyesweb.base.inputs import points_input
from pyeyesweb.catalog import Layer, describe
from pyeyesweb.data_models.inputs import Inputs
from pyeyesweb.data_models.results import Output, Result, Schema, Status
from pyeyesweb.base.core_feature import FrameFeature


@describe(Layer.PHYSICAL_SIGNALS, eyesweb="HitCellDetector")
class HitCellDetector(FrameFeature):
    """EyesWeb HitCellDetector: the grid cells hit by a list of 2D points. `process(points, *, timestamp=None)`.

    `points`: an `(N, 2)` array of `(x, y)` (`run` takes `(T, N, 2)`); `timestamp` is the timestamp in seconds. Output `cells`: `(n, 2)` int array of `(i, j)`, one per point in input order
    (an empty input gives an empty array, as EyesWeb outputs an empty list). With `clip_values=False` a point
    outside `[x_min, x_max] x [y_min, y_max]` makes the call `INVALID_INPUT` (`result.reason` says why).
    """
    _core_class = core.space.HitCellDetector
    _core_names = {"cells_along_x": "cells_x", "cells_along_y": "cells_y"}
    _unit_params = {"x_min": 1, "x_max": 1, "y_min": 1, "y_max": 1}  # lengths of the monitored area
    INPUTS = Inputs(points_input("points", None, "2D points to locate in the grid", dims=2))

    def _schema(self) -> Schema:
        return Schema(Output("cells", (None, 2), kind=int, components=("i", "j"),
                             doc="hit cell (row from y, column from x) of each point"))

    def _process(self, points: Any, timestamp: Optional[float]) -> Result:
        return self._to_result(self._block.process(points), timestamp)

    def _to_result(self, raw: Optional[np.ndarray], timestamp: float) -> Result:
        if raw is None:
            return self.no_output(Status.INVALID_INPUT, "point out of range (clip_values is off)", timestamp)
        return self.result(timestamp=timestamp, cells=raw)


__all__ = ["HitCellDetector"]
