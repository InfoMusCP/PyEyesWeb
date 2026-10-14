"""Regularity of a pulse train (EyesWeb BinaryPulsesRegularity)."""

from typing import Any, Optional

import numpy as np

from pyeyesweb._core import core
from pyeyesweb.base.core_feature import CoreFeature
from pyeyesweb.base.inputs import non_finite
from pyeyesweb.base.minimum_window import MinimumWindow
from pyeyesweb.catalog import Layer, describe
from pyeyesweb.data_models.feature import WindowedFeature
from pyeyesweb.data_models.inputs import Input, InputKind, Inputs
from pyeyesweb.data_models.results import Output, Result, Schema, Status


@describe(Layer.ANALYSIS_PRIMITIVE, eyesweb="binary_pulses_regularity (BinaryPulsesRegularity)")
class BinaryPulsesRegularity(MinimumWindow, WindowedFeature, CoreFeature):
    """Whether the pulses of a window are equally spaced (EyesWeb BinaryPulsesRegularity).

    `process(sample, *, timestamp=None)` takes one value of a single-channel signal per call, in which a non-zero value
    is a pulse (a step, a beat, the `is_peak` flag of `ScalarPeakDetector`). The feature buffers `window` samples and
    computes every `hop` samples (`WARMING_UP` while the first window fills, `NO_OUTPUT` between hops). The distance
    between the first two pulses of a window is the reference interval; the window is regular when at least three
    pulses are found and every other interval differs from the reference by at most `threshold` samples.

    Parameters
    ----------
    window : int
        Samples per window, >= 3 (three pulses are needed).
    hop : int, optional
        New samples between two windows (default 1).
    threshold : int, optional
        Tolerance in samples when two intervals are compared, >= 0 (default 0: intervals must be equal). Live.

    Returns
    -------
    Result
        `is_regular` (EyesWeb "Regularity Index"): the intervals between the pulses are equal within `threshold`;
        `pulse_count`: number of pulses (non-zero samples) in the window; `is_regularity_detected` (EyesWeb "Regularity
        Detected" trigger): `is_regular` on the first window after a window that was not. `INVALID_INPUT` for a
        window with NaN or infinite values.
    """
    _core_class = core.base.BinaryPulsesRegularity
    MIN_WINDOW = 3
    INPUTS = Inputs(Input("signal", InputKind.SAMPLE, (1,), doc="one value per call; a non-zero value is a pulse"))
    OUTPUTS = Schema(Output("is_regular", kind=bool, doc="the intervals between the pulses are equal within the threshold"),
                     Output("pulse_count", kind=int, doc="number of pulses in the window"),
                     Output("is_regularity_detected", kind=bool, doc="first regular window after a window that was not"))

    def __init__(self, window: int, hop: int = 1, **params: Any):
        super().__init__(window=window, hop=hop, **params)
        self._check_window()

    def _process_window(self, series: Any, *, timestamp: Optional[float] = None) -> Result:
        if reason := non_finite(series):
            return self.no_output(Status.INVALID_INPUT, reason, timestamp)
        regular, pulse_count, detected = self._block.process(np.asarray(series, dtype=float))
        return self.result(timestamp=timestamp, is_regular=regular, pulse_count=pulse_count, is_regularity_detected=detected)


__all__ = ["BinaryPulsesRegularity"]
