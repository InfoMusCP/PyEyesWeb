"""Peak events of a scalar signal (EyesWeb DANCE).

The block is a stateful stream over a scalar signal: `process(value, timestamp=None)` takes one sample per call and returns
an always-`OK` `Result` whose `timestamp` is the timestamp in seconds (`NaN` when not given); `reset()` restarts the stream.
"""

from typing import Any, Optional

import numpy as np

from pyeyesweb._core import core
from pyeyesweb.base.core_feature import FrameFeature
from pyeyesweb.catalog import Layer, describe
from pyeyesweb.data_models.inputs import Input, InputKind, Inputs
from pyeyesweb.data_models.results import Output, Result, Schema

_dance = core.dance


class _ScalarStream(FrameFeature):
    """A block fed one scalar sample per call."""

    _input_doc = "one value per call"

    def _inputs(self) -> Inputs:
        return Inputs(Input("signal", InputKind.SAMPLE, (1,), doc=self._input_doc))

    def _process(self, value: Any, timestamp: Optional[float]) -> Result:
        # a scalar, or the single channel of a (1,) sample
        return self._to_result(self._block.process(np.asarray(value, dtype=float).item()), timestamp)


@describe(Layer.ANALYSIS_PRIMITIVE, eyesweb="scalar_peak_detector")
class ScalarPeakDetector(_ScalarStream):
    """EyesWeb scalar_peak_detector. Output `is_peak` (bool): a peak was detected on this sample."""
    _core_class = _dance.ScalarPeakDetector
    _core_names = {"window": "buffer_length"}

    def _schema(self) -> Schema:
        return Schema(Output("is_peak", kind=bool))

    def _to_result(self, raw: bool, timestamp: Optional[float]) -> Result:
        return self.result(is_peak=raw, timestamp=timestamp)


__all__ = ["ScalarPeakDetector"]
