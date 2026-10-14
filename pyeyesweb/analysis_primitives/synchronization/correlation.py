"""Correlation-based synchronization matrices (EyesWeb GestureProcessingSynchronization).

`CorrelationsMatrix` and `GeneralisedAutoCorrelation` run on a static series and are windowed features (`window`,
`hop`, `_process_window`); `PartialRecurrenceSynchronization` transforms the matrix that `CorrelationsMatrix` returns, one matrix per call.
Every block declares its outputs as a `Schema` (`block.outputs`) and returns an always-`OK` `Result`.
"""

from itertools import count
from typing import Any, Optional, Sequence

import numpy as np

from pyeyesweb._core import core
from pyeyesweb.catalog import Layer, describe
from pyeyesweb.data_models.inputs import Input, InputKind, Inputs
from pyeyesweb.data_models.results import Output, Result, Schema, Status
from pyeyesweb.base.core_feature import FrameFeature
from pyeyesweb.base.inputs import non_finite

from ._blocks import _SeriesBlock

_sync = core.sync
_OutputType = _sync.GeneralisedAutoCorrelationOutputType


@describe(Layer.ANALYSIS_PRIMITIVE, eyesweb="CorrelationsMatrix (CPRMatrix)")
class CorrelationsMatrix(_SeriesBlock):
    """EyesWeb CorrelationsMatrix (CPRMatrix) of `number_of_inputs` signals.

    Input: one sample of `number_of_inputs` signals per call (constructor parameter, default 4). The feature buffers
    `window` samples and computes every `hop` samples; `_process_window(series)` takes one `(number_of_inputs, window)`
    series directly.

    Output `correlations_matrix`, shape `(number_of_inputs, number_of_inputs)`: 1 on the diagonal, max(0, Pearson) elsewhere.
    """
    _core_class = _sync.CorrelationsMatrix
    _core_names = {"number_of_inputs": "n_inputs"}
    _finite_inputs = True

    def _minimum_window(self, **overrides: Any) -> int:
        return 2  # a correlation needs two samples

    def _state_lost(self) -> None:
        super()._state_lost()
        self._buffer, self._pushed = None, 0  # a new `number_of_inputs` is a new frame size: the buffer starts again

    def _inputs(self) -> Inputs:
        return Inputs(Input("signals", InputKind.SAMPLE, (int(self._param("number_of_inputs", 4)),),  # C++ default
                            doc="one value per signal"))

    def _schema(self) -> Schema:
        number_of_inputs = int(self._param("number_of_inputs", 4))  # C++ default
        return Schema(Output("correlations_matrix", (number_of_inputs, number_of_inputs), doc="CPR matrix"))

    def _call_block(self, args: Sequence[Any]) -> np.ndarray:
        return self._block.process(list(args[0]))

    def _to_result(self, raw: np.ndarray, timestamp: float) -> Result:
        return self.finite_result(correlations_matrix=raw, timestamp=timestamp)


@describe(Layer.ANALYSIS_PRIMITIVE, eyesweb="PARS (PartialRecurrenceSynchronizationMatrix)")
class PartialRecurrenceSynchronization(FrameFeature):
    """EyesWeb PARS (PartialRecurrenceSynchronizationMatrix).

    Input: one square matrix per call, the `correlations_matrix` output of `CorrelationsMatrix` (kind `MATRIX`); `run` takes
    `(T, n, n)`.

    Output `synchronization_matrix`: partial recurrence synchronisation matrix, `(n, n)` with n taken from the input
    (data-dependent size).
    """
    _core_class = _sync.PARS

    def _inputs(self) -> Inputs:
        return Inputs(Input("correlations_matrix", InputKind.MATRIX, (None, None), doc="square matrix of CorrelationsMatrix"))

    def _schema(self) -> Schema:
        return Schema(Output("synchronization_matrix", (None, None), doc="partial recurrence synchronisation matrix"))

    def _process(self, frame: Any, timestamp: Optional[float]) -> Result:
        matrix = np.asarray(frame, dtype=float)
        if matrix.ndim == 2 and matrix.shape[0] != matrix.shape[1]:
            raise ValueError(f"PartialRecurrenceSynchronization: the matrix must be square, got shape {matrix.shape}")
        if reason := non_finite(matrix):
            return self.no_output(Status.INVALID_INPUT, reason, timestamp)
        return super()._process(matrix, timestamp)

    def _to_result(self, raw: np.ndarray, timestamp: float) -> Result:
        return self.result(synchronization_matrix=raw, timestamp=timestamp)


@describe(Layer.ANALYSIS_PRIMITIVE, eyesweb="generalised_auto_correlation")
class GeneralisedAutoCorrelation(_SeriesBlock):
    """EyesWeb generalised_auto_correlation of a series of samples.

    Input: samples of `C` channels, one per call; the feature buffers `window` samples and computes every `hop`
    samples. `_process_window(series)` takes one `(C, window)` series directly.

    Outputs `recurrence_rate[k]`: fraction of samples that recur within epsilon after a lag of `taus[k]` samples
    (both data-dependent size; `taus` is an integer output). A single entry in SCALAR output type.
    """
    _core_class = _sync.GeneralisedAutoCorrelation
    _finite_inputs = True

    def _minimum_window(self, **overrides: Any) -> int:
        params = {**self._params, **overrides}
        if params.get("output_type") == _OutputType.SCALAR:
            return 2
        tau_min, spread = int(params.get("tau_min", 1)), int(params.get("tau_spread", 10))  # C++ defaults
        # the core clamps the spread to 2N/3 and wants tau_min + spread < N
        return next(size for size in count(1) if tau_min + min(spread, 2 * size // 3) < size)

    def _inputs(self) -> Inputs:
        return Inputs(Input("signal", InputKind.SAMPLE, (None,), doc="one value per channel"))

    def _schema(self) -> Schema:
        return Schema(Output("recurrence_rate", (None,), doc="fraction of recurring samples per lag"),
                      Output("taus", (None,), kind=int, unit="samples", doc="lag of each recurrence rate"))

    def set_tau_min(self, tau_min: int) -> None:
        """Change the first lag at run time (EyesWeb run-time parameter)."""
        self._set_param("tau_min", int(tau_min))

    def _to_result(self, raw: np.ndarray, timestamp: float) -> Result:
        scalar = self._param("output_type", None) == _OutputType.SCALAR
        first = int(self._param("tau" if scalar else "tau_min", 1))  # C++ defaults
        return self.result(recurrence_rate=raw, taus=np.arange(first, first + len(raw)), timestamp=timestamp)


__all__ = ["CorrelationsMatrix", "PartialRecurrenceSynchronization", "GeneralisedAutoCorrelation"]
