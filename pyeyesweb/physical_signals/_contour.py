"""The base of the features that take one `(N, 2)` contour per call (physical signals and low-level shape)."""

from typing import Any, Optional

from pyeyesweb.base.core_feature import FrameFeature
from pyeyesweb.base.inputs import non_finite, points_input
from pyeyesweb.data_models.inputs import Inputs
from pyeyesweb.data_models.results import Result, Status

CONTOUR = points_input("contour", None, "contour points (x, y)", dims=2)


class ContourFeature(FrameFeature):
    """A block taking one `(N, 2)` contour per call; an empty or non-finite one is `INVALID_INPUT`."""
    INPUTS = Inputs(CONTOUR)

    def _process(self, contour: Any, timestamp: Optional[float]) -> Result:
        if reason := non_finite(contour):
            return self.no_output(Status.INVALID_INPUT, reason, timestamp)
        return self._to_result(self._block.process(contour), timestamp)
