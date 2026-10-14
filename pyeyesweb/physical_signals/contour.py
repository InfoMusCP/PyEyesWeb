"""Contour filtering (EyesWeb FilterContour). A contour is one frame of `(x, y)` points, an `(N, 2)` array."""

import numpy as np

from pyeyesweb._core import core
from pyeyesweb.physical_signals._contour import ContourFeature
from pyeyesweb.base.core_feature import XY
from pyeyesweb.catalog import Layer, describe
from pyeyesweb.data_models.results import Output, Result, Schema, Status


@describe(Layer.PHYSICAL_SIGNALS, eyesweb="filter_contour (FilterContour)")
class FilterContour(ContourFeature):
    """EyesWeb FilterContour. `process(contour, *, timestamp=None)`, `contour` an `(N, 2)` array of points (`run` takes
    `(T, N, 2)`); `timestamp` is the timestamp in seconds.

    Output `contour`: `(N, 2)` smoothed contour (components x, y). `NO_OUTPUT` when the window is not shorter
    than the contour.
    """
    _core_class = core.motion.FilterContour
    _core_names = {"window": "window_length", "gaussian_sigma": "sigma_value"}

    def _schema(self) -> Schema:
        return Schema(Output("contour", (None, 2), components=XY, doc="smoothed contour"))

    def _to_result(self, raw: np.ndarray, timestamp: float) -> Result:
        if len(raw) == 0:
            return self.no_output(Status.NO_OUTPUT, "contour not longer than the filter window", timestamp)
        return self.result(timestamp=timestamp, contour=raw)


__all__ = ["FilterContour"]
