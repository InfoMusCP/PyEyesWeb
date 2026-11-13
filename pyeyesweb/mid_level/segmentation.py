"""Segmentation of movement into gestures and pauses: ``GestureSegmenter``.

``GestureSegmenter`` turns an intensity signal into the start and end of gestures and measures how long the gestures and
the pauses between them last. Every feature declares its outputs as a ``Schema`` (``feature.outputs``) and returns a
``Result`` (see ``pyeyesweb.data_models``). Timestamps are optional and in seconds.
"""

from typing import Any, Optional

from pyeyesweb._core import core
from pyeyesweb.base.core_feature import FrameFeature
from pyeyesweb.catalog import Layer, describe
from pyeyesweb.data_models.inputs import Input, InputKind, Inputs
from pyeyesweb.data_models.results import Output, Result, Schema, Status
from pyeyesweb.base.inputs import non_finite, scalar

_motion = core.motion


@describe(Layer.MID_LEVEL, eyesweb="GestureSegmenter, MotionDuration (SteadyStateLength)")
class GestureSegmenter(FrameFeature):
    r"""Start and end of gestures from an intensity signal, and the duration of gestures and pauses.

    Segments a movement into gestures and pauses from a scalar intensity of the motion, for instance the kinetic energy
    of a skeleton (``KineticEnergy``). The intensity is smoothed with a Savitzky-Golay filter, a cubic polynomial fit to
    the newest ``filter_window_length`` samples and read at their centre, and a gesture is declared while the smoothed
    intensity :math:`\bar{I}` is at least ``firing_threshold``:

    .. math::

        \text{start: } \bar{I} \ge \theta, \qquad \text{end: } \bar{I} < \theta,

    where :math:`\theta` is the threshold. The smoothing delays the detection by ``(filter_window_length - 1) / 2``
    samples. There is a single threshold, with no hysteresis and no minimum duration: an intensity that hovers around
    :math:`\theta` opens and closes many short gestures, so set the threshold clearly above the level of the intensity
    at rest.

    A phase, gesture or pause, lasts from the sample where it begins to the sample where the next one begins:
    :math:`D = t(\text{end}) - t(\text{begin})`. Its duration is given on the sample that ends it. The time follows the
    timestamps when they are given, else ``sampling_rate``; without either, durations are in samples and the ``reason``
    says so. The phase running when the first smoothed sample arrives is counted from that sample.

    Input: the intensity, one scalar per call; ``process(intensity, *, timestamp=None)`` and
    ``run(intensity, *, timestamps=None)``.

    Parameters
    ----------
    firing_threshold : float, optional
        Level of the smoothed intensity at which a gesture is declared, in the unit of the intensity (for a kinetic
        energy, the squared unit of length per squared second). Defaults to ``0.1``. *(live)*
    filter_window_length : int, optional
        Number of samples of the Savitzky-Golay window: odd and at least 5 (other values raise ``ValueError``).
        Defaults to ``9``. *(structural)*
    continuous_output : bool, optional
        When ``False`` (default) a duration is given only on the sample that ends its phase, NaN on the others. When
        ``True`` every sample gives the durations of the last completed gesture and pause (NaN until one has ended).
        *(live)*
    sampling_rate : float, optional
        Sampling rate of the intensity in Hz, used when no timestamp is given. Defaults to ``None``. *(live)*

    Notes
    -----
    **Outputs.** ``smoothed_intensity``: the filtered intensity, in the unit of the input. ``is_gesturing``: ``True``
    while a gesture is running. ``is_gesture_start`` and ``is_gesture_end``: ``True`` on the sample that opens or closes
    a gesture. ``motion_duration`` and ``pause_duration``: the duration of the last completed gesture and pause, in
    seconds.

    **Statuses.** ``WARMING_UP`` for the first ``filter_window_length - 1`` samples (no output yet), ``OK`` afterwards;
    ``INVALID_INPUT`` for a NaN or infinite intensity or a timestamp that does not increase (the sample takes no time).
    A change of ``filter_window_length`` restarts the feature.

    The EyesWeb block smoothed a fixed 10-sample window without reading its newest sample, and took a noise flag that
    blocked the start of a gesture. Durations came from the separate block ``MotionDuration``, which counted samples.
    See the migration guide.

    Examples
    --------
    >>> import numpy as np
    >>> from pyeyesweb.mid_level import GestureSegmenter
    >>> intensity = np.concatenate([np.zeros(12), np.ones(15), np.zeros(15)])
    >>> record = GestureSegmenter(firing_threshold=0.5, sampling_rate=10.0).run(intensity)
    >>> print(np.flatnonzero(record.is_gesture_start), np.flatnonzero(record.is_gesture_end))
    [16] [31]
    >>> print(round(float(np.nanmax(record.motion_duration)), 3))  # seconds
    1.5
    """
    _core_class = _motion.GestureSegmenter
    _timed = True

    def _inputs(self) -> Inputs:
        return Inputs(Input("intensity", InputKind.SAMPLE, (1,), doc="intensity of the motion, e.g. its kinetic energy"))

    def _schema(self) -> Schema:
        return Schema(Output("smoothed_intensity", unit="<input>", doc="filtered intensity, once the window is full"),
                      Output("is_gesturing", kind=bool), Output("is_gesture_start", kind=bool),
                      Output("is_gesture_end", kind=bool),
                      Output("motion_duration", unit="s", doc="duration of the last completed gesture"),
                      Output("pause_duration", unit="s", doc="duration of the last completed pause"))

    def _process(self, intensity: Any, timestamp: Optional[float]) -> Result:
        if reason := non_finite(intensity):  # a rejected sample takes no time
            return self._no_output(Status.INVALID_INPUT, reason, timestamp)
        return self._to_result(self._block.process(scalar(intensity), self._time_step(timestamp)), timestamp)

    def _to_result(self, raw: Any, timestamp: Optional[float]) -> Result:
        if raw is None:
            return self._no_output(Status.WARMING_UP, "window filling", timestamp)
        smoothed, gesturing, start, end, motion, pause = raw
        return self._result(timestamp=timestamp, smoothed_intensity=smoothed, is_gesturing=gesturing,
                            is_gesture_start=start, is_gesture_end=end, motion_duration=motion, pause_duration=pause)


__all__ = ["GestureSegmenter"]
