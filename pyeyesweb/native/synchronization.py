"""Event-based and recurrence-based synchronization (EyesWeb, native C++).

Wraps the EyesWeb catalog *GestureProcessingSynchronization* ported to C++
in ``eyw_core.sync``:

* :class:`EventSynchronization` - Quian Quiroga event synchronization (Q, q)
  between two signals;
* :class:`SpikeSynchronization` - SPIKE-synchronization (Kreuz) among N >= 2
  signals;
* :class:`NonlinearInterdependence` - S(X|Y), S(Y|X) (Arnhold et al. 1999);
* :class:`RecurrenceRate` - generalised auto-correlation RR(tau) of the
  multichannel state.

All of them are :class:`~pyeyesweb.data_models.base.DynamicFeature`: they
take a ``(Time, Signals, Dims)`` window.  For the event-based measures the
signals are first reduced to scalars (the value when ``Dims == 1``, the
Euclidean norm otherwise, e.g. a velocity vector -> speed) and then turned
into binary event series (see :func:`extract_events`).

Every window is analysed independently, so overlapping sliding windows give
consistent results.
"""

from dataclasses import dataclass, field

import numpy as np

from pyeyesweb.data_models.base import DynamicFeature
from pyeyesweb.data_models.results import FeatureResult
from pyeyesweb.utils.validators import validate_integer, validate_numeric

from ._backend import require

_EVENT_MODES = ("peaks", "binary")


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def to_scalar_signals(data: np.ndarray) -> np.ndarray:
    """Reduce a ``(Time, Signals, Dims)`` tensor to ``(Time, Signals)`` float64.

    ``Dims == 1`` keeps the value; ``Dims > 1`` takes the Euclidean norm of
    each sample (e.g. velocity -> speed).  2-D input is returned as is.
    """
    data = np.asarray(data, dtype=np.float64)
    if data.ndim == 1:
        return data[:, None]
    if data.ndim == 2:
        return np.ascontiguousarray(data)
    if data.ndim != 3:
        raise ValueError(f"expected a (Time, Signals, Dims) array, got shape {data.shape}")
    if data.shape[2] == 1:
        return np.ascontiguousarray(data[:, :, 0])
    return np.ascontiguousarray(np.linalg.norm(data, axis=2))


def extract_events(signals: np.ndarray, mode: str = "peaks", peak_buffer: int = 5,
                   peak_threshold: float = 0.01) -> np.ndarray:
    """Turn continuous signals into binary event series (1 = event).

    Parameters
    ----------
    signals : numpy.ndarray of shape (Time, Signals)
    mode : {"peaks", "binary"}
        ``"peaks"``: an event at every local maximum found by the EyesWeb
        *ScalarPeakDetector* (run from scratch on each column, so the
        result only depends on the window).  ``"binary"``: the input already
        is an event series, every value > 0 is an event.
    peak_buffer : int
        Length of the peak detector buffer (samples).  Longer buffers ignore
        small wiggles but add about ``peak_buffer / 2`` samples of latency.
    peak_threshold : float
        Minimum peak-to-peak variation inside the buffer, in signal units.

    Returns
    -------
    numpy.ndarray of shape (Time, Signals), float64 with values 0 / 1.
    """
    signals = np.asarray(signals, dtype=np.float64)
    if signals.ndim != 2:
        raise ValueError(f"expected a (Time, Signals) array, got shape {signals.shape}")
    if mode == "binary":
        return (signals > 0).astype(np.float64)
    if mode != "peaks":
        raise ValueError(f"mode must be one of {_EVENT_MODES}, got {mode!r}")
    det = require().base.ScalarPeakDetector(int(peak_buffer), float(peak_threshold))
    out = np.zeros_like(signals)
    for c in range(signals.shape[1]):
        det.reset()
        out[:, c] = det.process(np.ascontiguousarray(signals[:, c]))
    return out


class _EventFeature(DynamicFeature):
    """Shared parameters of the event-based measures."""

    def __init__(self, events: str = "peaks", peak_buffer: int = 5, peak_threshold: float = 0.01):
        super().__init__()
        if events not in _EVENT_MODES:
            raise ValueError(f"events must be one of {_EVENT_MODES}, got {events!r}")
        self.events = events
        self.peak_buffer = validate_integer(peak_buffer, "peak_buffer", min_val=1, max_val=100_000)
        self.peak_threshold = validate_numeric(peak_threshold, "peak_threshold", min_val=0.0)
        self._eyw = require()

    def _events(self, data: np.ndarray) -> np.ndarray:
        signals = to_scalar_signals(data)
        if not np.all(np.isfinite(signals)):
            raise _InvalidWindow
        return extract_events(signals, self.events, self.peak_buffer, self.peak_threshold)


class _InvalidWindow(Exception):
    """Internal: the window contains NaN / inf values."""


# ---------------------------------------------------------------------------
# Event synchronization
# ---------------------------------------------------------------------------
@dataclass(slots=True)
class EventSynchronizationResult(FeatureResult):
    """Output contract of :class:`EventSynchronization`.

    Attributes
    ----------
    Q : float
        Synchronization strength in ``[0, 1]`` (1 = every event of one signal
        has a partner in the other within ``tau`` samples).
    q : float
        Delay behaviour in ``[-1, 1]``: ``> 0`` when the first signal leads
        (events of the second one tend to follow), ``< 0`` when it lags.
    events_x, events_y : int
        Number of events found in the two signals.
    """
    Q: float = 0.0
    q: float = 0.0
    events_x: int = 0
    events_y: int = 0


class EventSynchronization(_EventFeature):
    """Quian Quiroga event synchronization between two signals (EyesWeb).

    Read more: R. Quian Quiroga, T. Kreuz, P. Grassberger, *Event
    synchronization: a simple and fast method to measure synchronicity and
    time delay patterns*, Phys. Rev. E 66, 041904 (2002).

    Parameters
    ----------
    tau : int
        Maximum lag, in samples, between two events to call them synchronous.
    weighted : bool
        Weight each coupled pair by ``1 - (lag - 1) / tau`` instead of 1.
    events, peak_buffer, peak_threshold
        How events are extracted from the signals, see :func:`extract_events`.

    Examples
    --------
    >>> # speed of the two hands, 30 Hz, 4 s windows
    >>> es = EventSynchronization(tau=10, peak_buffer=15, peak_threshold=50.0)
    >>> window = SlidingWindow(max_length=120, n_signals=2, n_dims=1)
    """

    def __init__(self, tau: int = 5, weighted: bool = False, events: str = "peaks",
                 peak_buffer: int = 5, peak_threshold: float = 0.01):
        super().__init__(events, peak_buffer, peak_threshold)
        self.tau = validate_integer(tau, "tau", min_val=1, max_val=100_000)
        self.weighted = bool(weighted)

    def compute(self, data: np.ndarray) -> EventSynchronizationResult:
        """Event synchronization of a ``(Time, 2, Dims)`` window.

        Returns ``is_valid=False`` when the window does not contain exactly
        two signals, contains NaN, or one of the signals has no events.
        """
        try:
            ev = self._events(data)
        except _InvalidWindow:
            return EventSynchronizationResult(is_valid=False)
        if ev.shape[1] != 2:
            return EventSynchronizationResult(is_valid=False)
        impl = self._eyw.sync.EventSynchronization(self.tau, self.weighted, True)
        r = impl.compute(np.ascontiguousarray(ev[:, 0]), np.ascontiguousarray(ev[:, 1]))
        return EventSynchronizationResult(is_valid=bool(r.is_valid), Q=float(r.Q), q=float(r.q),
                                          events_x=int(r.events_x), events_y=int(r.events_y))


# ---------------------------------------------------------------------------
# SPIKE-synchronization
# ---------------------------------------------------------------------------
@dataclass(slots=True)
class SpikeSynchronizationResult(FeatureResult):
    """Output contract of :class:`SpikeSynchronization`.

    Attributes
    ----------
    sync : float
        SPIKE-synchronization in ``[0, 1]``: mean fraction of the other
        signals that have a coincident event, over all events.
    n_events : int
        Total number of events in the window (all signals).
    """
    sync: float = 0.0
    n_events: int = 0


class SpikeSynchronization(_EventFeature):
    """SPIKE-synchronization among N >= 2 signals (EyesWeb SpikeES / SpikyES).

    Two events of different signals are coincident when their distance is
    smaller than half of the shortest neighbouring inter-event interval, so
    no time-scale parameter is needed (Kreuz et al., J. Neurophysiol. 2015).

    Parameters
    ----------
    events, peak_buffer, peak_threshold
        How events are extracted from the signals, see :func:`extract_events`.
    """

    def compute(self, data: np.ndarray) -> SpikeSynchronizationResult:
        try:
            ev = self._events(data)
        except _InvalidWindow:
            return SpikeSynchronizationResult(is_valid=False)
        if ev.shape[1] < 2:
            return SpikeSynchronizationResult(is_valid=False)
        trains = [np.ascontiguousarray(ev[:, c]) for c in range(ev.shape[1])]
        r = self._eyw.sync.spike_synchronization(trains)
        return SpikeSynchronizationResult(is_valid=bool(r.is_valid), sync=float(r.sync_value),
                                          n_events=int(ev.sum()))


# ---------------------------------------------------------------------------
# Nonlinear interdependence
# ---------------------------------------------------------------------------
@dataclass(slots=True)
class NonlinearInterdependenceResult(FeatureResult):
    """Output contract of :class:`NonlinearInterdependence`.

    Attributes
    ----------
    s_xy : float
        S(X|Y): how much the first signal depends on the second (~1 strong,
        ~0 independent).
    s_yx : float
        S(Y|X): how much the second signal depends on the first.
    """
    s_xy: float = 0.0
    s_yx: float = 0.0


class NonlinearInterdependence(DynamicFeature):
    """Nonlinear interdependence of two scalar signals (EyesWeb).

    Read more: J. Arnhold, P. Grassberger, K. Lehnertz, C. E. Elger, *A robust
    method for detecting interdependences*, Physica D 134 (1999) 419-430.

    Parameters
    ----------
    embedding_dim : int
        Dimension ``m`` of the delay vectors (delay 1).
    k : int
        Number of nearest neighbours.

    Notes
    -----
    Cost is ``O(T^2)`` per window: keep windows below a few hundred samples
    for real-time use.
    """

    def __init__(self, embedding_dim: int = 3, k: int = 4):
        super().__init__()
        self.embedding_dim = validate_integer(embedding_dim, "embedding_dim", min_val=1, max_val=100)
        self.k = validate_integer(k, "k", min_val=1, max_val=1000)
        self._eyw = require()

    def compute(self, data: np.ndarray) -> NonlinearInterdependenceResult:
        x = to_scalar_signals(data)
        if x.shape[1] != 2 or not np.all(np.isfinite(x)):
            return NonlinearInterdependenceResult(is_valid=False)
        r = self._eyw.sync.nonlinear_interdependence(np.ascontiguousarray(x[:, 0]), np.ascontiguousarray(x[:, 1]),
                                                     self.embedding_dim, self.k)
        return NonlinearInterdependenceResult(is_valid=bool(r.is_valid), s_xy=float(r.s_xy), s_yx=float(r.s_yx))


# ---------------------------------------------------------------------------
# Recurrence rate (generalised auto-correlation)
# ---------------------------------------------------------------------------
@dataclass(slots=True)
class RecurrenceRateResult(FeatureResult):
    """Output contract of :class:`RecurrenceRate`.

    Attributes
    ----------
    taus : numpy.ndarray
        Lags (samples) at which RR is evaluated.
    rr : numpy.ndarray
        Recurrence rate RR(tau) in ``[0, 1]`` for each lag.
    dominant_tau : int
        Lag of the highest local maximum of RR (the most likely period of a
        repetitive movement); ``0`` when RR has no interior peak (no
        repetition inside the evaluated lags).
    """
    taus: np.ndarray = field(default_factory=lambda: np.zeros(0, dtype=int))
    rr: np.ndarray = field(default_factory=lambda: np.zeros(0))
    dominant_tau: int = 0


class RecurrenceRate(DynamicFeature):
    """Recurrence rate RR(tau) of the multichannel state (EyesWeb GeneralisedAutoCorrelation).

    The state at time t is the vector of all signals and dims of the window;
    ``RR(tau)`` is the fraction of pairs ``(t, t + tau)`` closer than
    ``epsilon`` (Marwan et al., Physics Reports 438, 2007).  Peaks of RR
    reveal the period of repetitive movements.

    Parameters
    ----------
    epsilon : float
        Neighbourhood radius, in the units of the data (after normalisation
        if ``normalize`` is True).
    tau_min, tau_spread : int
        RR is evaluated for ``tau = tau_min ... tau_min + tau_spread - 1``
        (bounded to 2/3 of the window length, as in EyesWeb).
    normalize : bool
        Z-score every channel inside the window first, so ``epsilon`` is in
        standard deviations and the measure does not depend on units.
    """

    def __init__(self, epsilon: float = 0.5, tau_min: int = 1, tau_spread: int = 30, normalize: bool = True):
        super().__init__()
        self.epsilon = validate_numeric(epsilon, "epsilon", min_val=0.0)
        self.tau_min = validate_integer(tau_min, "tau_min", min_val=1, max_val=1_000_000)
        self.tau_spread = validate_integer(tau_spread, "tau_spread", min_val=1, max_val=1_000_000)
        self.normalize = bool(normalize)
        self._eyw = require()

    def compute(self, data: np.ndarray) -> RecurrenceRateResult:
        data = np.asarray(data, dtype=np.float64)
        x = data.reshape(data.shape[0], -1)
        if x.shape[0] < 3 or not np.all(np.isfinite(x)):
            return RecurrenceRateResult(is_valid=False)
        if self.normalize:
            sd = x.std(axis=0)
            x = (x - x.mean(axis=0)) / np.where(sd > 0, sd, 1.0)
        rr = np.asarray(self._eyw.sync.generalised_autocorrelation(np.ascontiguousarray(x), self.epsilon,
                                                                   self.tau_min, self.tau_spread))
        taus = np.arange(self.tau_min, self.tau_min + len(rr))
        return RecurrenceRateResult(taus=taus, rr=rr, dominant_tau=_dominant_lag(taus, rr))


def _dominant_lag(taus: np.ndarray, rr: np.ndarray) -> int:
    """Lag of the highest interior local maximum of RR (0 if there is none).

    The edges are excluded: RR is naturally high at short lags (the state has
    not moved yet) and a maximum at the last lag is not a confirmed peak.
    """
    if len(rr) < 3:
        return 0
    inner = rr[1:-1]
    peaks = np.flatnonzero((inner > rr[:-2]) & (inner >= rr[2:]) & (inner > 0)) + 1
    return int(taus[peaks[np.argmax(rr[peaks])]]) if len(peaks) else 0
