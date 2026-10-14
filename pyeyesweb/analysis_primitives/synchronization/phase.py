"""Phase Synchronization analysis for paired signals.

This module implements the [Synchronization][pyeyesweb.analysis_primitives.synchronization.PhaseLockingValue]
feature, which measures the phase locking between two time series using the Phase Locking Value (PLV).
"""

from typing import Optional

from pyeyesweb.catalog import Layer, describe
from pyeyesweb.data_models.inputs import Inputs
from pyeyesweb.data_models.results import Output, Result, Schema
from pyeyesweb._core import core
from pyeyesweb.utils.validators import validate_and_normalize_filter_params

from ._blocks import _TrainPairBlock, _train


@describe(Layer.ANALYSIS_PRIMITIVE)
class PhaseLockingValue(_TrainPairBlock):
    """Real-time phase synchronization analyzer for two signals.

    !!! note
        Computes the Phase Locking Value (PLV) between two signals after optional bandpass filtering and Hilbert
        transform.

    Read more in the [User Guide](../../user_guide/theoretical_framework/analysis_primitives/synchronization.md).

    Input: one sample of each signal per call, `process(first_signal, second_signal, *, timestamp=None)` and
    `run(first_signal, second_signal, *, timestamps=None)`; each signal is a scalar per call. The feature buffers `window`
    samples and computes every `hop` samples (`process` returns `WARMING_UP` while the first window fills and
    `NO_OUTPUT` between hops). `_process_window(first_signal, second_signal)` computes one complete window directly.

    The Hilbert phase is only meaningful for narrow-band signals: on broadband movement data the PLV stays near 1
    whatever the coupling. Nothing is filtered unless `filter_params` is given, so band-limit the signals first (or pass
    `filter_params`). For 2D or 3D data reduce each participant to one signal first, for example the tangential `velocity`
    output of `Kinematics`, or the projection on the dominant axis of the movement.

    Parameters
    ----------
    window : int
        Samples per window.
    hop : int, optional
        New samples between two windows (default 1).
    filter_params : dict, optional
        Parameters for the bandpass filter applied before phase estimation (none by default).
        See [validate_and_normalize_filter_params](../utils/signal_processing.md#validate_and_normalize_filter_params)
        for details.

    Examples
    --------
    >>> sync = PhaseLockingValue(window=100, filter_params={'low': 1.0, 'high': 10.0})
    """

    OUTPUTS = Schema(
        Output("plv", doc="Phase Locking Value in [0, 1]; 1 is perfect phase synchronization."),
    )

    _core_class = core.sync.PhaseLockingValue
    _finite_inputs = True

    def __init__(self, window: int, hop: int = 1, filter_params=None):
        super().__init__(window, hop, filter_params=validate_and_normalize_filter_params(filter_params))

    def _minimum_window(self, **overrides) -> int:
        params = {**self._params, **overrides}
        return 28 if params.get("filter_params") else 1  # filtfilt pads 3 * filter length (27) samples

    def _inputs(self) -> Inputs:
        return Inputs(_train("first_signal", "one value per call"), _train("second_signal", "one value per call"))

    @property
    def filter_params(self):
        """Parameters for the bandpass pre-filter."""
        return self._params["filter_params"]

    @filter_params.setter
    def filter_params(self, value):
        self._set_param("filter_params", validate_and_normalize_filter_params(value))

    def _to_result(self, raw: float, timestamp: Optional[float]) -> Result:
        return self.result(plv=raw, timestamp=timestamp)


__all__ = ['PhaseLockingValue']
