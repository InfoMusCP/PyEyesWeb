"""Synchronization of events: event synchronization, MECS, SPIKE-synchronization, interdependence and sequences.

Event trains are sample streams in which a non-zero value is an event. The features that evaluate a window of samples
(``window``, ``hop``) are windowed features; `SequenceDetector` is stateful per sample and takes one sample per call.
Their results are ``OK`` unless the docstring of the feature says otherwise.
"""

from typing import Any, Optional, Sequence, Tuple

import numpy as np

from pyeyesweb._core import core
from pyeyesweb.catalog import Layer, describe
from pyeyesweb.data_models.inputs import Input, InputKind, Inputs
from pyeyesweb.data_models.results import Output, Result, Schema, Status
from pyeyesweb.base.core_feature import FrameFeature
from pyeyesweb.base.inputs import train

from ._blocks import _SeriesBlock, _TrainPairBlock, _train

_sync = core.sync
_SpikeSyncMode = _sync.SpikeSyncMode


def _series_inputs(feature: Any, doc: str) -> Inputs:
    """One input per time series (`number_of_inputs`, default 2), each with one channel per event class."""
    number_of_series = int(feature._param("number_of_inputs", 2))  # C++ default
    return Inputs(*(Input(f"series{index + 1}", InputKind.SAMPLE, (None,), doc=doc) for index in range(number_of_series)))


class _NonOverlapping:
    """Mixin, placed before the series block, of a block that accumulates across executions: consecutive windows must
    not overlap (the samples of the overlap would be counted twice), so `hop` is `window` (the default)."""

    def __init__(self, window: int, hop: Optional[int] = None, **params: Any):
        super().__init__(window, window if hop is None else hop, **params)

    @classmethod
    def _validated(cls, window: int, hop: int) -> tuple:
        window, hop = super()._validated(window, hop)
        if hop != window:
            raise ValueError(f"{cls.__name__} accumulates across executions and cannot take overlapping windows: hop "
                             f"must equal window (got window={window}, hop={hop}); change both with configure()")
        return window, hop


@describe(Layer.ANALYSIS_PRIMITIVE, eyesweb="Event Sync")
class EventSynchronization(_NonOverlapping, _TrainPairBlock):
    r"""Event synchronization of two event trains: how often events of one series follow those of the other.

    Quantifies the coordination of two sequences of discrete events (for example the onsets of two performers'
    gestures or beats) without assuming a fixed rhythm, following the event synchronization measure of Quian Quiroga
    and colleagues. With :math:`m_x` and :math:`m_y` events in the first and second train and :math:`c(y|x)` the
    number of events of the second train that follow an event of the first one within ``tau`` samples (and
    :math:`c(x|y)` the converse), the feature reports

    .. math::

        Q = \frac{c(x|y) + c(y|x)}{\sqrt{m_x m_y}} \in [0, 1], \qquad
        q = \frac{c(y|x) - c(x|y)}{\sqrt{m_x m_y}} \in [-1, 1].

    :math:`Q = 1` means that every event of each train has a partner in the other one; :math:`q > 0` means that the
    first train leads, :math:`q < 0` that the second one does. Simultaneous events count as synchronous and
    contribute to :math:`Q` but not to :math:`q`. With ``weighted=True`` a pair at lag :math:`d` (in samples)
    counts with the weight :math:`1 - (d - 1)/\tau` instead of 1.

    The queues and counts are accumulated across windows, so consecutive windows must not overlap: ``hop`` equals
    ``window`` (its default) and any other value raises ``ValueError``.

    Parameters
    ----------
    window : int
        Samples per window (no default). Changing it keeps the newest samples. *(live)*
    hop : int, optional
        Samples between two results; ``None`` (default) means ``window``, and no other value is accepted.
        *(live)*
    tau : int, optional
        Largest lag, in samples, at which an event of one train is matched to an event of the other (default 5).
        *(live)*
    reset_every_buffer : bool, optional
        If ``True``, the accumulated events and counts are cleared at every window, so that each window is evaluated
        on its own and events are not matched across the boundary of two windows (default ``False``).
        *(structural)*
    weighted : bool, optional
        Weight each matched pair by its lag as above (default ``False``). *(live)*

    Notes
    -----
    **Inputs.** ``process(first_signal, second_signal, *, timestamp=None)`` takes one value of each train per call,
    non-zero is an event; ``run(first_signal, second_signal, *, timestamps=None)`` takes two 1-D series.

    **Outputs.** ``synchronization`` (dimensionless, in [0, 1]): :math:`Q`; ``delay`` (dimensionless, in [-1, 1]):
    :math:`q`, positive when the first series leads.

    **Statuses.** ``WARMING_UP`` (``"k of N samples"``) while the first window fills; ``OK`` once per window.

    **Corrected in the core.** The coincidence window is now ``0 < lag <= tau`` (an event used to expire one sample
    too early, so ``tau = 1`` matched nothing); the weight of ``weighted=True`` is the one above (an integer division
    made it 0 for nearly every pair); ``delay`` is positive when the first series leads (the sign was reversed); and
    events are no longer credited twice or never. Overlapping windows are refused (they counted the overlapped events
    twice).

    Examples
    --------
    >>> import numpy as np
    >>> first, second = np.zeros(60), np.zeros(60)
    >>> first[[5, 25, 45]] = 1
    >>> second[[7, 27, 56]] = 1
    >>> record = EventSynchronization(window=60, tau=3).run(first, second)
    >>> round(float(record.synchronization[-1]), 2), round(float(record.delay[-1]), 2)
    (0.67, 0.67)
    """
    _core_class = _sync.EventSynchronization
    _INPUTS = Inputs(_train("first_signal"), _train("second_signal"))

    def _schema(self) -> Schema:
        return Schema(Output("synchronization", doc="Q in [0, 1]"), Output("delay", doc="q in [-1, 1]"))

    def _to_result(self, raw: Tuple[float, float], timestamp: float) -> Result:
        return self._result(synchronization=raw[0], delay=raw[1], timestamp=timestamp)


class _MECSBlock(_NonOverlapping, _SeriesBlock):
    """A MECS block accumulates across executions."""

    def _to_result(self, raw: Tuple[np.ndarray, np.ndarray], timestamp: float) -> Result:
        return self._result(synchronization=raw[0][0], events=raw[1][0], timestamp=timestamp)

    def _call_block(self, args: Sequence[Any]) -> Any:
        return self._block.process(list(args))


@describe(Layer.ANALYSIS_PRIMITIVE, eyesweb="MECS Algorithm v2")
class EventSynchronizationMECS(_MECSBlock):
    r"""Multi-event-class synchronization of several event series (MECS), one index per event class.

    Extends the event synchronization of two trains to ``number_of_inputs`` series that carry events of several
    classes (for example gestures of different types, one channel per class), and reports for every class how
    synchronous the series are. For each class and each pair of series, the coincidences :math:`S_{ij}` are the pairs
    of events within ``tau`` samples, weighted by the ``kernel``; with :math:`m_i` and :math:`m_j` the event counts of
    the two series, the pair term is

    .. math::

        \min\left(1, \; \frac{S_{ij}}{\sqrt{m_i m_j}}\right),

    and the synchronization of the class is the mean of the pair terms over the :math:`N(N-1)/2` pairs of the
    :math:`N` series. The result is accumulated across windows, so consecutive windows must not overlap: ``hop``
    equals ``window`` (its default) and any other value raises ``ValueError``.

    Parameters
    ----------
    window : int
        Samples per window (no default). Changing it keeps the newest samples. *(live)*
    hop : int, optional
        Samples between two results; ``None`` (default) means ``window``, and no other value is accepted.
        *(live)*
    number_of_inputs : int, optional
        Number of event series (default 2); ``process`` and ``run`` take that many inputs, ``series1``,
        ``series2``, ... *(structural)*
    number_of_event_classes : int, optional
        Number of event classes (default 3), the number of channels of each series and the size of the outputs.
        *(structural)*
    tau : int, optional
        Largest lag, in samples, at which two events are considered coincident (default 10). *(structural)*
    kernel : {"uniform", "linear", "gaussian"}, optional
        Weight given to a coincidence as a function of the lag: constant (``"uniform"``, the default), decreasing
        linearly (``"linear"``), or Gaussian (``"gaussian"``). *(live)*
    gaussian_sigma, gaussian_mean : float, optional
        Standard deviation and mean, in samples, of the Gaussian kernel; used only with ``kernel="gaussian"``
        (default ``None``: the defaults of the core). *(live)*

    Notes
    -----
    **Inputs.** ``process(series1, series2, ..., *, timestamp=None)`` takes one sample per series with one channel
    per event class (non-zero is an event); ``run`` takes ``(T, number_of_event_classes)`` series.

    **Outputs.** ``synchronization`` (dimensionless, shape ``(number_of_event_classes,)``, in [0, 1]): index of each
    class; ``events`` (count, same shape): the number of events of each class in the window, summed over the series.

    **Statuses.** ``WARMING_UP`` (``"k of N samples"``) while the first window fills; ``OK`` once per window.

    **Corrected in the core.** The number of pairs was evaluated as :math:`(N!/2)(N-2)!` instead of
    :math:`N(N-1)/2`, and the pair term shrank with the number of events (two identical series of four events gave
    0.25 instead of 1); it is the normalization above. Only the former "version 2" of the algorithm is provided.

    Examples
    --------
    >>> import numpy as np
    >>> first, second = np.zeros((60, 1)), np.zeros((60, 1))
    >>> first[[5, 25, 45], 0] = 1
    >>> second[[7, 27, 46], 0] = 1
    >>> record = EventSynchronizationMECS(window=60, number_of_event_classes=1, tau=3).run(first, second)
    >>> record.synchronization[-1], record.events[-1]
    (array([1.]), array([6.]))
    """
    _core_class = _sync.EventSynchronizationMECS
    _core_names = {"number_of_inputs": "time_series_number", "number_of_event_classes": "event_class_number"}

    def _inputs(self) -> Inputs:
        return _series_inputs(self, "events of one class per channel")

    def _schema(self) -> Schema:
        number_of_classes = int(self._param("number_of_event_classes", 3))  # C++ default
        return Schema(Output("synchronization", number_of_classes, doc="sync index of each event class"),
                      Output("events", number_of_classes, doc="event count of each event class"))

    def _call_block(self, args: Sequence[Any]) -> Any:
        return self._block.process(list(args), 0)


@describe(Layer.ANALYSIS_PRIMITIVE, eyesweb="EventSynchronization_Interdependence")
class NonlinearInterdependence(_TrainPairBlock):
    r"""Nonlinear interdependence between two signals: how much the neighbours of one reflect those of the other.

    Quantifies a generalized, possibly nonlinear, dependence between two movement signals that a linear correlation
    would miss, following the nonlinear interdependence of Arnhold and colleagues. Each signal is embedded in a state
    space of dimension ``embedding_dimension``; for each state of :math:`X` the ``neighbours`` nearest states in
    time are found, and :math:`S(X|Y)` compares the distances of these states in the space of :math:`X` with the
    distances of the corresponding states in the space of :math:`Y`. It is close to 1 for two signals that determine
    each other (identical signals give 1) and close to 0 for independent signals. The two values are generally
    different; their asymmetry is read as the direction of the coupling.

    Parameters
    ----------
    window : int
        Samples per window, at least ``neighbours + 1`` (no default). Changing it keeps the newest samples. *(live)*
    hop : int, optional
        Samples between two results, ``1 <= hop <= window`` (default 1). *(live)*
    embedding_dimension : int, optional
        Dimension of the state-space embedding built from each signal (default 1). *(live)*
    neighbours : int, optional
        Number of nearest neighbours used for each state (default 2); the window must exceed it. *(live)*

    Notes
    -----
    **Inputs.** ``process(first_signal, second_signal, *, timestamp=None)`` takes one scalar of each signal per call;
    ``run(first_signal, second_signal, *, timestamps=None)`` takes two 1-D series.

    **Outputs.** ``first_to_second_interdependence`` :math:`S(X|Y)` and ``second_to_first_interdependence``
    :math:`S(Y|X)` (dimensionless, normally in [0, 1]); ``threshold`` (dimensionless): the threshold value that the
    block computes from the parameters, :math:`(k/m)^{2/m}` for ``neighbours`` :math:`k` and ``embedding_dimension``
    :math:`m`.

    **Statuses.** ``WARMING_UP`` (``"k of N samples"``) while the first window fills, ``NO_OUTPUT`` between two
    windows when ``hop > 1``, ``INVALID_INPUT`` when a result is not finite.

    **Corrected in the core.** The threshold used an exclusive-or on integers instead of the power above.

    Examples
    --------
    >>> import numpy as np
    >>> x = np.random.default_rng(0).normal(size=100)
    >>> record = NonlinearInterdependence(window=100, neighbours=3).run(x, x ** 3)
    >>> round(float(record.first_to_second_interdependence[-1]), 2)
    0.97
    """
    _core_class = _sync.EventSynchronizationInterdependence
    _INPUTS = Inputs(_train("first_signal", "signal"), _train("second_signal", "signal"))

    def _minimum_window(self, **overrides: Any) -> int:
        params = {**self._params, **overrides}
        return int(params.get("neighbours", 2)) + 1  # C++ default; the core wants neighbours < samples

    def _schema(self) -> Schema:
        return Schema(Output("first_to_second_interdependence", doc="S(X|Y)"),
                      Output("second_to_first_interdependence", doc="S(Y|X)"), Output("threshold"))

    def _to_result(self, raw: Tuple[float, float, float], timestamp: float) -> Result:
        return self._finite_result(first_to_second_interdependence=raw[0], second_to_first_interdependence=raw[1],
                                  threshold=raw[2], timestamp=timestamp)


@describe(Layer.ANALYSIS_PRIMITIVE, eyesweb="SPIKE sync")
class SpikeSynchronization(_SeriesBlock):
    r"""SPIKE-synchronization of several spike trains: the share of spikes that have a coincident partner.

    Measures how many of the events (spikes) of a group of ``number_of_inputs`` event trains occur together with an
    event of another train, without a time scale parameter: coincidence is decided adaptively from the local spike
    intervals (SPIKE-synchronization, Kreuz and colleagues). Each spike receives a coincidence indicator, 1 if it
    coincides with a spike of the other trains and 0 if it does not, and the degree of synchronization is the mean
    of the indicator over all the spikes of all the trains (a spike shared by two trains counts twice),

    .. math::

        \mathrm{degree} \in [0, 1], \qquad \mathrm{distance} = 1 - \mathrm{degree}.

    Parameters
    ----------
    window : int
        ``"binary"``: samples per window (no default). Changing it keeps the newest samples. ``"timings"``: the number
        of spikes of each train (the core needs the same number in every train). *(live)*
    hop : int, optional
        Samples between two results, ``1 <= hop <= window`` (default 1); not used in ``"timings"`` mode, where every
        call gives a result. *(live)*
    number_of_inputs : int, optional
        Number of spike trains (default 2), the number of channels of the input. *(structural)*
    mode : {"binary", "timings"}, optional
        How the trains are given (default ``"binary"``): ``"binary"`` for one channel per train sampled in time, a
        positive value being a spike; ``"timings"`` for the spike times themselves, one call per set of trains. *(structural)*

    Notes
    -----
    **Inputs.** ``"binary"``: ``process(trains, *, timestamp=None)`` takes one sample with one channel per train;
    ``run(trains, *, timestamps=None)`` takes ``(T, number_of_inputs)``. ``"timings"``:
    ``process(spike_times, *, timestamp=None)`` takes one ``(number_of_inputs, window)`` matrix, one row per train
    holding its spike times (any unit, ``> 0`` and increasing in each row), and returns the result for those trains;
    ``run(spike_times, *, timestamps=None)`` takes ``(T, number_of_inputs, window)``, one set of trains per row of the
    recorder, and nothing is carried from one call to the next. Spike times that are not ``> 0`` or not increasing
    give ``INVALID_INPUT``; a matrix of another shape (trains with different numbers of spikes) raises ``ValueError``.

    **Outputs.** ``degree`` (dimensionless, in [0, 1]): SPIKE-synchronization; ``distance`` (dimensionless, in
    [0, 1]): ``1 - degree``; ``profile`` (dimensionless, one value per sample of the window): the coincidence
    indicator of the merged spikes at each sample, -1 where no train has a spike, available in ``"binary"`` mode
    only (empty otherwise).

    **Statuses.** ``"binary"``: ``WARMING_UP`` (``"k of N samples"``) while the first window fills, ``NO_OUTPUT``
    between two windows when ``hop > 1``. ``"timings"``: ``OK`` for every call.

    **Corrected in the core.** In binary mode the degree and the distance were swapped; the degree was the mean over
    the distinct spike positions instead of over all spikes (for the trains 10, 20, 30 and 10, 21, 45 it was 0.6, it is
    0.667); the merging of timings by "last train wins" was removed.

    Examples
    --------
    >>> import numpy as np
    >>> trains = np.zeros((50, 2))
    >>> trains[[5, 20, 35], 0] = 1
    >>> trains[[5, 21, 40], 1] = 1
    >>> record = SpikeSynchronization(window=50).run(trains)
    >>> float(record.degree[-1]), float(record.distance[-1])
    (1.0, 0.0)

    The same trains as spike times (here in the same order, the second train 1 sample late for its last spike):

    >>> times = np.array([[5.0, 20.0, 35.0], [5.0, 21.0, 40.0]])
    >>> result = SpikeSynchronization(window=3, mode="timings").process(times)
    >>> float(result.degree), float(result.distance)
    (1.0, 0.0)
    """
    _core_class = _sync.SpikeES
    _core_names = {"number_of_inputs": "number_of_input_trains"}

    def _inputs(self) -> Inputs:
        number_of_trains = int(self._param("number_of_inputs", 2))  # C++ default
        if self._mode == _SpikeSyncMode.TIMINGS:
            return Inputs(Input("spike_times", InputKind.MATRIX, (number_of_trains, self.window),
                                doc="spike times, one row per train, increasing and > 0"))
        return Inputs(Input("trains", InputKind.SAMPLE, (number_of_trains,), doc="one value per spike train"))

    def _window_changed(self) -> None:
        self._outputs_changed()  # in "timings" mode the inputs have ``window`` columns

    def _schema(self) -> Schema:
        return Schema(Output("degree", doc="SPIKE-synchronization in [0, 1]"), Output("distance", doc="1 - degree"),
                      Output("profile", (None,), doc="merged coincidence per sample, BINARY mode only"))

    @property
    def _mode(self) -> Any:
        return self._param("mode", _SpikeSyncMode.BINARY)  # C++ default

    def process(self, *samples: Any, timestamp: Optional[float] = None) -> Result:
        if self._mode != _SpikeSyncMode.TIMINGS:
            return super().process(*samples, timestamp=timestamp)
        times = np.asarray(samples[0], dtype=float)
        if times.size == 0:
            return self._no_output(Status.INVALID_INPUT, "empty sample", timestamp)
        if (times <= 0).any():
            return self._no_output(Status.INVALID_INPUT, "spike times must be > 0", timestamp)
        if (np.diff(times, axis=1) <= 0).any():
            return self._no_output(Status.INVALID_INPUT, "spike times must increase within each train", timestamp)
        return self._to_result(self._call_block([times]), timestamp)

    def _call_block(self, args: Sequence[Any]) -> Any:
        trains = args[0]
        if self._mode == _SpikeSyncMode.BINARY:
            trains = np.where(trains > 0, 1.0, -1.0)
        return self._block.process(list(trains))

    def _to_result(self, raw: Tuple[Any, float, float], timestamp: float) -> Result:
        profile, degree, distance = raw
        return self._result(degree=degree, distance=distance, profile=None if profile is None else profile[0], timestamp=timestamp)


@describe(Layer.ANALYSIS_PRIMITIVE, eyesweb="SequenceDetector")
class SequenceDetector(FrameFeature):
    r"""Detector of a given sequence of integer events in a stream, one sample per call.

    Recognizes when a short ordered pattern of events (for example the successive gestures of an exercise, each coded
    with an integer) is performed, and counts the completed patterns. At every sample the input is the id of the
    event that happens (0 when none); the sequence is completed when its ids occur in order with at most
    ``inter_event_time`` samples between two consecutive ones; a longer gap breaks it.

    Parameters
    ----------
    sequence : str, optional
        The ids of the sequence, integers separated by spaces (default ``"1 2"``). *(structural)*
    inter_event_time : int, optional
        Largest distance in samples between two consecutive events of the sequence (default 1: the events
        are on consecutive samples; with 2 one sample without event may separate them). *(live)*
    any_order : bool, optional
        If ``True`` the sequence is also detected in the reversed order (default ``False``). *(structural)*

    Notes
    -----
    **Inputs.** ``process(event, *, timestamp=None)`` takes the integer id of the event of this sample, 0 for none;
    ``run(event, *, timestamps=None)`` takes a 1-D series of ids.

    **Outputs.** ``is_completed`` (bool): the sequence was completed by this sample; ``sequence_count`` (count): the
    number of sequences completed so far.

    **Statuses.** Always ``OK``.

    **Corrected in the core.** The detector of the reversed order started at the last position, so a lone first
    element was detected; when both directions were completed by the same sample (a palindromic or one-element
    sequence) the count rose by 2, it rises by 1.

    Examples
    --------
    >>> detector = SequenceDetector(sequence="1 2 3")
    >>> [int(detector.process(event).sequence_count) for event in [1, 2, 3, 0, 1, 2, 3]]
    [0, 0, 1, 1, 1, 1, 2]
    """
    _core_class = _sync.SequenceDetector
    _INPUTS = Inputs(Input("event", InputKind.SAMPLE, (1,), doc="event id, 0 = none", integer=True))

    def _schema(self) -> Schema:
        return Schema(Output("is_completed", kind=bool), Output("sequence_count", kind=int))

    def _process(self, event: Any, timestamp: Optional[float]) -> Result:
        return self._to_result(self._block.process(int(train(event)[0])), timestamp)

    def _to_result(self, raw: bool, timestamp: float) -> Result:
        return self._result(is_completed=raw, sequence_count=self._block.number_of_sequences, timestamp=timestamp)


__all__ = ["EventSynchronization", "EventSynchronizationMECS", "NonlinearInterdependence", "SpikeSynchronization",
           "SequenceDetector"]
