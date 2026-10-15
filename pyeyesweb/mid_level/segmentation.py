"""Segmentation of movement into gestures and pauses: ``GestureSegmenter`` and ``MotionDuration``.

``GestureSegmenter`` turns an intensity signal into the start and end of gestures; ``MotionDuration`` measures the
length of the motion and pause phases of a segmentation signal. Every feature declares its outputs as a ``Schema``
(``feature.outputs``) and returns a ``Result`` (see ``pyeyesweb.data_models``). Timestamps are optional and in seconds.
"""

from typing import Any, Optional

import numpy as np

from pyeyesweb._core import core
from pyeyesweb.base.core_feature import CoreFeature, FrameFeature
from pyeyesweb.catalog import Layer, describe
from pyeyesweb.data_models.inputs import Input, InputKind, Inputs
from pyeyesweb.data_models.recorder import Recorder
from pyeyesweb.data_models.results import Output, Result, Schema, Status
from pyeyesweb.base.inputs import non_finite, scalar

_motion = core.motion


@describe(Layer.MID_LEVEL, eyesweb="MotionDuration (SteadyStateLength)")
class MotionDuration(FrameFeature):
    """Duration of the last motion and pause phases of a segmentation signal.

    Measures how long the phases of motion and of stillness last in a sequence of samples of a segmentation signal, for
    instance the ``is_gesturing`` output of ``GestureSegmenter``. A sample is *motion* when the signal is not zero and a
    *pause* when it is zero. The phases are counted in samples, and the length of a phase is reported when the phase
    ends, on the first sample of the next one: a motion duration when a pause begins, a pause duration when a motion
    begins. The phase that is running when the first sample arrives is counted from that sample, whether or not it began
    earlier.

    Input: the segmentation signal, one scalar per call; ``process(frame, *, timestamp=None)``.

    Parameters
    ----------
    sampling_rate : float, optional
        Sampling rate of the signal, in Hz. With a rate the durations are in seconds; without one (``None``, the
        default) they are in frames, that is, samples. *(live)*
    continuous_output : bool, optional
        When ``False`` (default) a call produces an output only on the sample that ends a phase, and only the duration
        of that phase. When ``True`` every call produces both durations, those of the last completed motion and pause
        phases (0 until a phase of that kind has ended). *(live)*

    Notes
    -----
    **Outputs.** ``motion_duration`` and ``pause_duration``: length of the last completed motion and pause phase, in
    seconds with ``sampling_rate`` and in frames without; not negative. A call updates at most one of them unless
    ``continuous_output`` is set.

    **Statuses.** ``NO_OUTPUT`` for a sample that ends no phase (``continuous_output=False``); ``INVALID_INPUT`` for a
    NaN or infinite sample.

    Examples
    --------
    >>> import numpy as np
    >>> from pyeyesweb.mid_level import MotionDuration
    >>> record = MotionDuration(sampling_rate=10.0).run([0, 0, 1, 1, 1, 0, 0])
    >>> print(np.nanmax(record.pause_duration), np.nanmax(record.motion_duration))
    0.2 0.3
    """
    _core_class = _motion.MotionDuration

    def _inputs(self) -> Inputs:
        return Inputs(Input("signal", InputKind.SAMPLE, (1,), doc="segmentation signal, non-zero while moving"))

    def _schema(self) -> Schema:
        unit = "s" if self._param("sampling_rate", None) else "frames"
        return Schema(Output("motion_duration", unit=unit, doc="duration of the last completed motion phase"),
                      Output("pause_duration", unit=unit, doc="duration of the last completed pause phase"))

    def _process(self, signal: Any, timestamp: Optional[float]) -> Result:
        return self._to_result(self._block.process(scalar(signal)), timestamp)

    def _to_result(self, raw: Any, timestamp: Optional[float]) -> Result:
        motion, pause = raw
        if motion is None and pause is None:
            return self._no_output(Status.NO_OUTPUT, "no phase change", timestamp)
        return self._result(motion_duration=motion, pause_duration=pause, timestamp=timestamp)


@describe(Layer.MID_LEVEL, eyesweb="GestureSegmenter")
class GestureSegmenter(CoreFeature):
    r"""Start and end of gestures from an intensity signal, with optional noise gating.

    Segments a movement into gestures from a scalar intensity of the motion, for instance the kinetic energy of a
    skeleton (``KineticEnergy``). The intensity is smoothed with a Savitzky-Golay filter (polynomial of order 3, applied
    to the last 10 samples with a window of ``filter_window_length`` samples) and a gesture is declared while the
    smoothed intensity :math:`\bar{I}` is at least ``firing_threshold``:

    .. math::

        \text{start: } \bar{I} \ge \theta \;\text{and not noise}, \qquad \text{end: } \bar{I} < \theta,

    where :math:`\theta` is the threshold. A gesture can start only while the optional ``noise`` flag is not set, which
    keeps a motion that is judged to be noise (no gesture) from opening a gesture; once started, it ends when the smoothed intensity falls
    below the threshold, whatever the flag. In a skeleton pipeline the intensity is the ``kinetic_energy`` output of
    ``KineticEnergy`` and the flag the ``is_noisy`` output of ``MotionNoiseDetector`` computed on the same frames, passed as it is (``True`` = noise, no gesture can start);
    without a flag the feature segments any one-dimensional signal. The smoothing delays the detection by a few samples.

    Inputs, in call order: ``intensity``, a scalar per call, and ``noise``, optional (1 or ``True`` while the motion is
    judged to be noise (no gesture); 0 by default): ``process(intensity, noise=False, *, timestamp=None)`` and ``run(intensity,
    noise=None, *, timestamps=None)``.

    Parameters
    ----------
    firing_threshold : float, optional
        Level of the smoothed intensity at which a gesture is declared, in the unit of the intensity (for a kinetic
        energy, the squared unit of length per squared second). Defaults to ``0.1``. *(live)*
    filter_window_length : int, optional
        Number of samples of the Savitzky-Golay window. It must be odd and shorter than the 10-sample series: ``5``,
        ``7`` or ``9`` (other values raise ``ValueError``). Defaults to ``9``. *(structural)*

    Notes
    -----
    **Outputs.** ``smoothed_intensity``: the filtered intensity, in the unit of the input. ``is_gesturing``: ``True``
    while a gesture is running. ``is_gesture_start`` and ``is_gesture_end``: ``True`` on the sample that opens or closes
    a gesture.

    **Statuses.** ``WARMING_UP`` for the first 10 samples (no output yet), ``OK`` afterwards; ``INVALID_INPUT`` for a
    NaN or infinite intensity or flag. A change of ``filter_window_length`` restarts the filter.

    The window of 15 samples that is the default of the original block cannot be used (the filter needs a window shorter
    than the series), so the default here is 9.

    Examples
    --------
    >>> import numpy as np
    >>> from pyeyesweb.mid_level import GestureSegmenter
    >>> intensity = np.concatenate([np.zeros(12), np.ones(15), np.zeros(15)])
    >>> record = GestureSegmenter(firing_threshold=0.5).run(intensity)
    >>> print(np.flatnonzero(record.is_gesture_start), np.flatnonzero(record.is_gesture_end))
    [17] [32]
    """
    _core_class = _motion.GestureSegmenter

    def _inputs(self) -> Inputs:
        return Inputs(Input("intensity", InputKind.SAMPLE, (1,), doc="intensity of the motion, e.g. its kinetic energy"),
                      Input("noise", InputKind.SAMPLE, (1,), doc="1 while the motion is judged to be noise (no gesture) (default 0)", optional=True))

    def _schema(self) -> Schema:
        return Schema(Output("smoothed_intensity", unit="<input>", doc="filtered intensity, once the window is full"),
                      Output("is_gesturing", kind=bool), Output("is_gesture_start", kind=bool),
                      Output("is_gesture_end", kind=bool))

    def process(self, intensity: Any, noise: Any = 0.0, *, timestamp: Optional[float] = None) -> Result:
        if reason := non_finite(intensity) or non_finite(noise):
            return self._no_output(Status.INVALID_INPUT, reason, timestamp)
        return self._to_result(self._block.process(scalar(intensity), bool(scalar(noise))), timestamp)

    def run(self, intensity: Any, noise: Optional[Any] = None, *, timestamps: Optional[Any] = None,
            reset: bool = True) -> Recorder:
        return super().run(intensity, np.zeros(len(intensity)) if noise is None else noise, timestamps=timestamps,
                           reset=reset)

    def _to_result(self, raw: Any, timestamp: Optional[float]) -> Result:
        if raw is None:
            return self._no_output(Status.WARMING_UP, "window filling", timestamp)
        smoothed, gesturing, start, end = raw
        return self._result(timestamp=timestamp, smoothed_intensity=smoothed, is_gesturing=gesturing,
                           is_gesture_start=start, is_gesture_end=end)


__all__ = ["GestureSegmenter", "MotionDuration"]
