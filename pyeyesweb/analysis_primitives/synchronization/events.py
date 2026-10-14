"""Synchronization of events: Event Sync, MECS, SPIKE sync, sequences (EyesWeb GestureProcessingSynchronization).

Event trains are sample streams in which a non-zero value is an event. The blocks that EyesWeb runs on buffered
series are windowed features (`window`, `hop`, `_process_window(*series)` with one `(channels, window)` array per
input); the block that is stateful per sample (`SequenceDetector`) takes one sample per call.

Every block declares its outputs as a `Schema` (`block.outputs`) and returns a `Result`; all of them are always
`OK` except where a block's docstring says otherwise (outputs that EyesWeb does not emit on a call are flagged in
`result.valid` and hold `NaN` / `0` / `False`).
"""

from typing import Any, Optional, Sequence, Tuple

import numpy as np

from pyeyesweb._core import core
from pyeyesweb.catalog import Layer, describe
from pyeyesweb.data_models.inputs import Input, InputKind, Inputs
from pyeyesweb.data_models.feature import WindowedFeature
from pyeyesweb.data_models.results import Output, Result, Schema
from pyeyesweb.base.core_feature import FrameFeature
from pyeyesweb.base.inputs import train

from ._blocks import _SeriesBlock, _TrainPairBlock, _train

_sync = core.sync
_SpikeSyncMode = _sync.SpikeSyncMode


def _series_inputs(feature: Any, doc: str) -> Inputs:
    """One input per time series (`time_series_number`, default 2), each with one channel per event class."""
    number_of_series = int(feature._param("time_series_number", 2))  # C++ default
    return Inputs(*(Input(f"series{index + 1}", InputKind.SAMPLE, (None,), doc=doc) for index in range(number_of_series)))


class _NonOverlapping:
    """Mixin, placed before the series block, of a block that accumulates across executions: consecutive windows must
    not overlap (the samples of the overlap would be counted twice), so `hop` is `window` (the default)."""

    def __init__(self, window: int, hop: Optional[int] = None, **params: Any):
        super().__init__(window, window if hop is None else hop, **params)

    @classmethod
    def _validated(cls, window: int, hop: int) -> tuple:
        window, hop = WindowedFeature._validated(window, hop)
        if hop != window:
            raise ValueError(f"{cls.__name__} accumulates across executions and cannot take overlapping windows: hop "
                             f"must equal window (got window={window}, hop={hop}); change both with configure()")
        return window, hop


@describe(Layer.ANALYSIS_PRIMITIVE, eyesweb="Event Sync")
class EventSynchronization(_NonOverlapping, _TrainPairBlock):
    """EyesWeb Event Sync of two event trains.

    Inputs: `ts1`, `ts2`, one sample each per call (non-zero = event). The feature buffers `window` samples and
    computes every `hop` samples; `_process_window(ts1, ts2)` takes two `(1, window)` series directly. The block
    accumulates across windows, so they must not overlap: `hop` is `window` (the default) and any other value raises
    `ValueError`.

    Outputs `synchronization` (Quian Quiroga's Q) in [0, 1] and `delay` (q) in [-1, 1]. q > 0 means the first
    series leads.
    """
    _core_class = _sync.EventSynchronization
    INPUTS = Inputs(_train("ts1"), _train("ts2"))

    def _schema(self) -> Schema:
        return Schema(Output("synchronization", doc="Q in [0, 1]"), Output("delay", doc="q in [-1, 1]"))

    def _to_result(self, raw: Tuple[float, float], timestamp: float) -> Result:
        return self.result(synchronization=raw[0], delay=raw[1], timestamp=timestamp)


class _MECSBlock(_NonOverlapping, _SeriesBlock):
    """A MECS block accumulates across executions."""

    def _to_result(self, raw: Tuple[np.ndarray, np.ndarray], timestamp: float) -> Result:
        return self.result(synchronization=raw[0][0], events=raw[1][0], timestamp=timestamp)

    def _call_block(self, args: Sequence[Any]) -> Any:
        return self._block.process(list(args))


@describe(Layer.ANALYSIS_PRIMITIVE, eyesweb="MECS Algorithm v2")
class EventSynchronizationMECS(_MECSBlock):
    """EyesWeb MECS Algorithm (v2), multi event class synchronisation of several event series.

    Inputs: `time_series_number` inputs (constructor parameter, default 2) `series1`, `series2`, ..., each one
    sample per call with one channel per event class (non-zero = event). The feature buffers `window` samples and
    computes every `hop` samples; `_process_window(*series)` takes one `(classes, window)` array per input directly.

    Outputs `synchronization[m]` and `events[m]` (EyesWeb "Sync vector" and "Lead vector", the latter an event
    count), shape `(M,)`, M = `event_class_number` (default 3).
    """
    _core_class = _sync.EventSynchronizationMECS

    def _inputs(self) -> Inputs:
        return _series_inputs(self, "events of one class per channel")

    def _schema(self) -> Schema:
        number_of_classes = int(self._param("event_class_number", 3))  # C++ default
        return Schema(Output("synchronization", number_of_classes, doc="sync index of each event class"),
                      Output("events", number_of_classes, doc="event count of each event class"))

    def _call_block(self, args: Sequence[Any]) -> Any:
        return self._block.process(list(args), 0)


@describe(Layer.ANALYSIS_PRIMITIVE, eyesweb="EventSynchronization_Interdependence")
class NonlinearInterdependence(_TrainPairBlock):
    """EyesWeb EventSynchronization_Interdependence of two signals.

    Inputs: `x`, `y`, one sample each per call. The feature buffers `window` samples and computes every `hop`
    samples; `_process_window(x, y)` takes two `(1, window)` series directly.

    Outputs `xy` = S(X|Y), `yx` = S(Y|X): nonlinear interdependence; `threshold`: the block's threshold output.
    """
    _core_class = _sync.EventSynchronizationInterdependence
    INPUTS = Inputs(_train("x", "signal"), _train("y", "signal"))

    def _minimum_window(self, **overrides: Any) -> int:
        params = {**self._params, **overrides}
        return int(params.get("neighbours", 2)) + 1  # C++ default; the core wants neighbours < samples

    def _schema(self) -> Schema:
        return Schema(Output("xy", doc="S(X|Y)"), Output("yx", doc="S(Y|X)"), Output("threshold"))

    def _to_result(self, raw: Tuple[float, float, float], timestamp: float) -> Result:
        return self.finite_result(xy=raw[0], yx=raw[1], threshold=raw[2], timestamp=timestamp)


@describe(Layer.ANALYSIS_PRIMITIVE, eyesweb="SPIKE sync")
class SpikeSynchronization(_SeriesBlock):
    """EyesWeb SPIKE sync of `number_of_input_trains` trains (constructor parameter, default 2).

    Input: `trains`, one sample per call with one channel per train (BINARY mode: -1 / +1, spike = +1; TIMINGS
    mode: spike times). The feature buffers `window` samples and computes every `hop` samples;
    `_process_window(trains)` takes one `(trains, window)` series directly.

    Outputs `degree`: SPIKE-synchronization in [0, 1]; `distance` = 1 - degree; `profile` (data-dependent size):
    per-sample merged coincidence (-1 = no spike), valid in BINARY mode only.
    """
    _core_class = _sync.SpikeES

    def _inputs(self) -> Inputs:
        number_of_trains = int(self._param("number_of_input_trains", 2))  # C++ default
        return Inputs(Input("trains", InputKind.SAMPLE, (number_of_trains,), doc="one value per spike train"))

    def _schema(self) -> Schema:
        return Schema(Output("degree", doc="SPIKE-synchronization in [0, 1]"), Output("distance", doc="1 - degree"),
                      Output("profile", (None,), doc="merged coincidence per sample, BINARY mode only"))

    @property
    def _mode(self) -> Any:
        return self._param("mode", _SpikeSyncMode.BINARY)  # C++ default

    def process(self, *samples: Any, timestamp: Optional[float] = None) -> Result:
        if self._mode == _SpikeSyncMode.TIMINGS:
            raise TypeError("TIMINGS mode takes spike times, not samples: use _process_window(trains)")
        return super().process(*samples, timestamp=timestamp)

    def _call_block(self, args: Sequence[Any]) -> Any:
        trains = args[0]
        if self._mode == _SpikeSyncMode.BINARY:
            trains = np.where(trains > 0, 1.0, -1.0)
        return self._block.process(list(trains))

    def _to_result(self, raw: Tuple[Any, float, float], timestamp: float) -> Result:
        profile, degree, distance = raw
        return self.result(degree=degree, distance=distance, profile=None if profile is None else profile[0], timestamp=timestamp)


@describe(Layer.ANALYSIS_PRIMITIVE, eyesweb="SequenceDetector")
class SequenceDetector(FrameFeature):
    """EyesWeb SequenceDetector, one sample per call.

    Input: `event`, the integer id of the event of this sample (the numbers of `sequence`), 0 = none.

    Outputs `completed` (a sequence was completed by this event) and `sequences` (total completed so far).
    """
    _core_class = _sync.SequenceDetector
    INPUTS = Inputs(Input("event", InputKind.SAMPLE, (1,), doc="event id, 0 = none", integer=True))

    def _schema(self) -> Schema:
        return Schema(Output("completed", kind=bool), Output("sequences", kind=int))

    def _process(self, event: Any, timestamp: Optional[float]) -> Result:
        return self._to_result(self._block.process(int(train(event)[0])), timestamp)

    def _to_result(self, raw: bool, timestamp: float) -> Result:
        return self.result(completed=raw, sequences=self._block.number_of_sequences, timestamp=timestamp)


__all__ = ["EventSynchronization", "EventSynchronizationMECS", "NonlinearInterdependence", "SpikeSynchronization",
           "SequenceDetector"]
