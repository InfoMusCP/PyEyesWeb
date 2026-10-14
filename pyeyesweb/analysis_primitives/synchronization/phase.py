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
    whatever the coupling. Nothing is filtered unless `low_frequency` and `high_frequency` are given, so band-limit the signals first (or pass
    them). For 2D or 3D data reduce each participant to one signal first, for example the tangential `velocity`
    output of `Kinematics`, or the projection on the dominant axis of the movement.

    Parameters
    ----------
    window : int
        Samples per window.
    hop : int, optional
        New samples between two windows (default 1).
    low_frequency, high_frequency : float, optional
        Edges in Hz of the zero-phase band-pass (Butterworth, order 4) applied before phase estimation; both or
        neither (no filtering by default). `0 < low_frequency < high_frequency < sampling_rate / 2`.
    sampling_rate : float, optional
        Sampling rate of the signals in Hz; required to filter, unused otherwise.

    Examples
    --------
    >>> sync = PhaseLockingValue(window=100, low_frequency=1.0, high_frequency=10.0, sampling_rate=100.0)
    """

    _OUTPUTS = Schema(
        Output("phase_locking_value", doc="Phase Locking Value in [0, 1]; 1 is perfect phase synchronization."),
    )

    _core_class = core.sync.PhaseLockingValue
    _finite_inputs = True

    def __init__(self, window: int, hop: int = 1, *, low_frequency: Optional[float] = None,
                 high_frequency: Optional[float] = None, sampling_rate: Optional[float] = None):
        if (low_frequency is None) != (high_frequency is None):
            raise ValueError("PhaseLockingValue: low_frequency and high_frequency go together (or neither: no filtering)")
        super().__init__(window, hop, low_frequency=low_frequency, high_frequency=high_frequency,
                         sampling_rate=sampling_rate)

    def _block_params(self, params: dict) -> dict:
        """The band-pass as the block takes it: `filter_params=(low, high, rate)`, validated here. Without both edges
        (a live change one edge at a time passes through that state) nothing is filtered."""
        low, high, rate = (params.get(name) for name in ("low_frequency", "high_frequency", "sampling_rate"))
        if low is None or high is None:
            return {}
        if rate is None:
            raise ValueError("PhaseLockingValue: filtering needs sampling_rate (Hz)")
        return {"filter_params": validate_and_normalize_filter_params((low, high, rate))}

    def _minimum_window(self, **overrides) -> int:
        params = {**self._params, **overrides}
        filtering = params.get("low_frequency") is not None and params.get("high_frequency") is not None
        return 28 if filtering else 1  # filtfilt pads 3 * filter length (27) samples

    def _inputs(self) -> Inputs:
        return Inputs(_train("first_signal", "one value per call"), _train("second_signal", "one value per call"))

    def _to_result(self, raw: float, timestamp: Optional[float]) -> Result:
        return self._result(phase_locking_value=raw, timestamp=timestamp)


__all__ = ['PhaseLockingValue']
