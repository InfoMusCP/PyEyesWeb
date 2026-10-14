"""Segmentation of movement into gestures and pauses (EyesWeb MotionAnalysis).

Every feature declares its outputs as a `Schema` (`feature.outputs`) and returns a `Result` (see
`pyeyesweb.data_models`). `status` is `OK` when the call produced output, `WARMING_UP` while a window fills
(GestureSegmenter) and `NO_OUTPUT` when the block only emits on some activations (MotionDuration). Timestamps
are optional and in seconds (`timestamp`); the result reports them as `result.timestamp`.
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
    """EyesWeb MotionDuration (SteadyStateLength).

    Input: the segmentation signal, a scalar sample per call (`process(signal, timestamp=None)`; non-zero = motion).

    Outputs `motion_duration` and `pause_duration`: length of the last completed phase (frames, or seconds with
    `sampling_rate`). EyesWeb updates at most one of them per frame: status is `OK` with `valid` set for
    the updated output, `NO_OUTPUT` when neither is updated. `timestamp` is the
    timestamp in seconds (`NaN` when not given).
    """
    _core_class = _motion.MotionDuration

    def _inputs(self) -> Inputs:
        return Inputs(Input("signal", InputKind.SAMPLE, (1,), doc="segmentation signal, non-zero while moving"))

    def _schema(self) -> Schema:
        return Schema(Output("motion_duration", doc="duration of the last completed motion phase"),
                      Output("pause_duration", doc="duration of the last completed pause phase"))

    def _process(self, signal: Any, timestamp: Optional[float]) -> Result:
        return self._to_result(self._block.process(scalar(signal)), timestamp)

    def _to_result(self, raw: Any, timestamp: Optional[float]) -> Result:
        motion, pause = raw
        if motion is None and pause is None:
            return self.no_output(Status.NO_OUTPUT, "no phase change", timestamp)
        return self.result(motion_duration=motion, pause_duration=pause, timestamp=timestamp)


@describe(Layer.MID_LEVEL, eyesweb="GestureSegmenter")
class GestureSegmenter(CoreFeature):
    """EyesWeb GestureSegmenter, the segmentation: start and end of gestures from an intensity signal.

    Inputs, in call order: `intensity`, a scalar sample per call, and `noise`, optional (`process(intensity, noise=False,
    timestamp=None)`, `run(intensities, noises=None, timestamps=None)`): 1 while the motion is judged random, which
    keeps a gesture from starting. Without it the feature segments any 1D signal.

    The EyesWeb block is the composition of three features: `KineticEnergy` gives the intensity of a skeleton,
    `MotionNoiseDetector` the noise flag of the same frames, and this feature smooths the intensity with a Savitzky-Golay
    filter (`filter_window_length`) and declares a gesture while it is at least `firing_threshold`::

        energy, detector = KineticEnergy(skeleton=...), MotionNoiseDetector(skeleton=...)
        segmenter = GestureSegmenter(firing_threshold=...)
        result = segmenter.process(energy.process(frame, timestamp=t)["kinetic_energy"],
                                   detector.process(frame, timestamp=t)["noise"])

    `firing_threshold` is in the unit of the intensity: the energy of data in millimetres is in mm^2.

    `smoothed_intensity`, `gesturing`, `gesture_start` and `gesture_end` are emitted once the 10-sample window is full:
    before that the status is `WARMING_UP` and they are not produced; afterwards `OK`.
    """
    _core_class = _motion.GestureSegmenter

    def _inputs(self) -> Inputs:
        return Inputs(Input("intensity", InputKind.SAMPLE, (1,), doc="intensity of the motion, e.g. its kinetic energy"),
                      Input("noise", InputKind.SAMPLE, (1,), doc="1 while the motion is judged random (default 0)", optional=True))

    def _schema(self) -> Schema:
        return Schema(Output("smoothed_intensity", doc="filtered intensity, once the window is full"),
                      Output("gesturing", kind=bool), Output("gesture_start", kind=bool),
                      Output("gesture_end", kind=bool))

    def process(self, intensity: Any, noise: Any = 0.0, *, timestamp: Optional[float] = None) -> Result:
        if reason := non_finite(intensity) or non_finite(noise):
            return self.no_output(Status.INVALID_INPUT, reason, timestamp)
        return self._to_result(self._block.process(scalar(intensity), bool(scalar(noise))), timestamp)

    def run(self, intensity: Any, noise: Optional[Any] = None, *, timestamps: Optional[Any] = None,
            reset: bool = True) -> Recorder:
        return super().run(intensity, np.zeros(len(intensity)) if noise is None else noise, timestamps=timestamps,
                           reset=reset)

    def _to_result(self, raw: Any, timestamp: Optional[float]) -> Result:
        if raw is None:
            return self.no_output(Status.WARMING_UP, "window filling", timestamp)
        smoothed, gesturing, start, end = raw
        return self.result(timestamp=timestamp, smoothed_intensity=smoothed, gesturing=gesturing, gesture_start=start,
                           gesture_end=end)


__all__ = ["GestureSegmenter", "MotionDuration"]
