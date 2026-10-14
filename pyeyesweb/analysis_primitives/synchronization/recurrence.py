"""Recurrence plots (EyesWeb GestureProcessingSynchronization), computed on a static series: windowed features
(`window`, `hop`, `_process_window(*series)` with one `(channels, window)` array per input)."""

import numpy as np

from pyeyesweb._core import core
from pyeyesweb.catalog import Layer, describe
from pyeyesweb.data_models.inputs import Input, InputKind, Inputs
from pyeyesweb.data_models.results import Output, Result, Schema

from ._blocks import _SeriesBlock

_sync = core.sync


@describe(Layer.ANALYSIS_PRIMITIVE, eyesweb="RecurrencePlot (RecurrenceMatrix)")
class RecurrencePlot(_SeriesBlock):
    """EyesWeb RecurrencePlot (RecurrenceMatrix) of a series of states.

    Input: samples of `C` channels (the state vector), one per call; the feature buffers `window` samples and
    computes every `hop` samples. `_process_window(series)` takes one `(C, window)` series directly.

    Output `plot`: `(N, N)` 0/1 matrix, N = number of samples (data-dependent size); `plot[i, j] = 1` iff the
    distance between states i and j is strictly below epsilon (row i's epsilon with `use_multiple_epsilons`).
    `order` is the Minkowski order (`order <= 0` or infinite: max norm). Always `OK`.
    """
    _core_class = _sync.RecurrencePlot
    _finite_inputs = True

    def _inputs(self) -> Inputs:
        return Inputs(Input("series", InputKind.SAMPLE, (None,), doc="state vector, one value per channel"))

    def _schema(self) -> Schema:
        return Schema(Output("plot", (None, None), doc="recurrence matrix, 1 = recurrence"))

    def _to_result(self, raw: np.ndarray, timestamp: float) -> Result:
        return self.result(plot=raw, timestamp=timestamp)


@describe(Layer.ANALYSIS_PRIMITIVE, eyesweb="CrossRecurrencePlot (CrossRecurrenceMatrix)")
class CrossRecurrencePlot(_SeriesBlock):
    """EyesWeb CrossRecurrencePlot (CrossRecurrenceMatrix) of two series of states with the same channel count.

    Inputs: `series1`, `series2`, one sample each per call; the feature buffers `window` samples and computes every
    `hop` samples. `_process_window(series1, series2)` takes two `(C, N1)` and `(C, N2)` series directly (the
    lengths may differ).

    Output `plot`: `(N1, N2)` 0/1 matrix (data-dependent size). `order` is the Minkowski order (`order <= 0` or
    infinite: max norm). Always `OK`.
    """
    _core_class = _sync.CrossRecurrencePlot
    _finite_inputs = True

    def _inputs(self) -> Inputs:
        return Inputs(Input("series1", InputKind.SAMPLE, (None,), doc="state vector, one value per channel"),
                      Input("series2", InputKind.SAMPLE, (None,), doc="state vector, one value per channel"))

    def _schema(self) -> Schema:
        return Schema(Output("plot", (None, None), doc="cross-recurrence matrix, 1 = recurrence"))

    def _to_result(self, raw: np.ndarray, timestamp: float) -> Result:
        return self.result(plot=raw, timestamp=timestamp)


__all__ = ["RecurrencePlot", "CrossRecurrencePlot"]
