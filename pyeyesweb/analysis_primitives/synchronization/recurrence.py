"""Recurrence plots (EyesWeb GestureProcessingSynchronization), computed on a static series: windowed features
(`window`, `hop`, `_process_window(*series)` with one `(channels, window)` array per input)."""

from typing import Any, Optional, Sequence

import numpy as np

from pyeyesweb._core import core
from pyeyesweb.catalog import Layer, describe
from pyeyesweb.data_models.inputs import Input, InputKind, Inputs
from pyeyesweb.data_models.results import Output, Result, Schema

from ._blocks import _SeriesBlock

_sync = core.sync


class _Epsilons:
    """Mixin, placed before the series block, of the plots with one threshold per sample: `multiple_epsilons=None` is
    `epsilon` for each of the `window` samples (the core wants one value per sample when `use_multiple_epsilons`)."""

    def __init__(self, window: int, hop: int = 1, *, multiple_epsilons: Optional[Sequence[float]] = None, **params: Any):
        super().__init__(window, hop, multiple_epsilons=multiple_epsilons, **params)

    def _block_params(self, params: dict) -> dict:
        if params.get("multiple_epsilons") is None:
            params = {**params, "multiple_epsilons": [params.get("epsilon", 0.5)] * self.window}  # C++ default
        return super()._block_params(params)

    def _window_changed(self) -> None:
        if self._params.get("multiple_epsilons") is None:
            self._invalidate_block()  # one epsilon per sample of the new window


@describe(Layer.ANALYSIS_PRIMITIVE, eyesweb="RecurrencePlot (RecurrenceMatrix)")
class RecurrencePlot(_Epsilons, _SeriesBlock):
    """EyesWeb RecurrencePlot (RecurrenceMatrix) of a series of states.

    Input: samples of `C` channels (the state vector), one per call; the feature buffers `window` samples and
    computes every `hop` samples. `_process_window(series)` takes one `(C, window)` series directly.

    Output `recurrence_matrix`: `(N, N)` 0/1 matrix, N = number of samples (data-dependent size); `plot[i, j] = 1` iff the
    distance between states i and j is strictly below epsilon (row i's epsilon with `use_multiple_epsilons`; `multiple_epsilons`
    `None` is `epsilon` for every row).
    `order` is the Minkowski order (`order <= 0` or infinite: max norm). Always `OK`.
    """
    _core_class = _sync.RecurrencePlot
    _finite_inputs = True

    def _inputs(self) -> Inputs:
        return Inputs(Input("series", InputKind.SAMPLE, (None,), doc="state vector, one value per channel"))

    def _schema(self) -> Schema:
        return Schema(Output("recurrence_matrix", (None, None), doc="recurrence matrix, 1 = recurrence"))

    def _to_result(self, raw: np.ndarray, timestamp: float) -> Result:
        return self._result(recurrence_matrix=raw, timestamp=timestamp)


@describe(Layer.ANALYSIS_PRIMITIVE, eyesweb="CrossRecurrencePlot (CrossRecurrenceMatrix)")
class CrossRecurrencePlot(_Epsilons, _SeriesBlock):
    """EyesWeb CrossRecurrencePlot (CrossRecurrenceMatrix) of two series of states with the same channel count.

    Inputs: `first_series`, `second_series`, one sample each per call; the feature buffers `window` samples and computes
    every `hop` samples. `_process_window(first_series, second_series)` takes two `(C, N1)` and `(C, N2)` series directly (the
    lengths may differ).

    Output `cross_recurrence_matrix`: `(N1, N2)` 0/1 matrix (data-dependent size). `order` is the Minkowski order (`order <= 0` or
    infinite: max norm). Always `OK`.
    """
    _core_class = _sync.CrossRecurrencePlot
    _finite_inputs = True

    def _inputs(self) -> Inputs:
        return Inputs(Input("first_series", InputKind.SAMPLE, (None,), doc="state vector, one value per channel"),
                      Input("second_series", InputKind.SAMPLE, (None,), doc="state vector, one value per channel"))

    def _schema(self) -> Schema:
        return Schema(Output("cross_recurrence_matrix", (None, None), doc="cross-recurrence matrix, 1 = recurrence"))

    def _to_result(self, raw: np.ndarray, timestamp: float) -> Result:
        return self._result(cross_recurrence_matrix=raw, timestamp=timestamp)


__all__ = ["RecurrencePlot", "CrossRecurrencePlot"]
