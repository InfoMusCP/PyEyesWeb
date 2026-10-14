"""Noise test of the skeleton motion (EyesWeb GestureSegmenter, IsUserMotionRandomic2): per-joint speed variances."""

from typing import Any, Optional, Sequence, Tuple

from pyeyesweb._core import core
from pyeyesweb.base.core_feature import FrameFeature
from pyeyesweb.base.inputs import labelled_set, non_finite, points_input
from pyeyesweb.catalog import Layer, describe
from pyeyesweb.data_models.inputs import Inputs
from pyeyesweb.data_models.results import Output, Result, Schema, Status
from pyeyesweb.base.labels import LabelGuard
from pyeyesweb.skeletons import with_skeleton


@describe(Layer.LOW_LEVEL, eyesweb="GestureSegmenter (IsUserMotionRandomic2)")
class MotionNoiseDetector(LabelGuard, FrameFeature):
    """The noise test of the EyesWeb GestureSegmenter (IsUserMotionRandomic2): is the motion of the skeleton random?

    Input: one skeleton frame per call, an `(N, 3)` array in the order of `labels`, or a dict `label -> (x, y, z)`
    (`labels` are needed for array input). `process(frame, timestamp=None)`; `timestamp` is the frame time in seconds,
    from which the block derives its time step (see `run`, `sampling_rate`).

    Output `noise`, valid on every call: the variance of the speed of each joint over its last 10 frames is averaged over
    5 frames, and the motion is noise while that mean is below `noise_threshold`. EyesWeb quirks are kept: only the last
    joint in label order with a full window counts, and the flag is true until 14 speeds were seen. It feeds the second
    input of `GestureSegmenter`; the kinetic energy of the same frames, from `KineticEnergy`, feeds the first.
    """
    _core_class = core.motion.MotionNoiseDetector
    _timed = True
    _unit_params = {"noise_threshold": 2}  # variance of a speed: length^2

    def __init__(self, labels: Optional[Sequence[str]] = None, skeleton: Any = None, **params: Any):
        labels, params = with_skeleton(skeleton, labels, params)
        super().__init__(labels=None if labels is None else list(labels), **params)
        self._set_labels(labels)

    @property
    def labels(self) -> Optional[Tuple[str, ...]]:
        """The watched joints, which are also the joint names of array input."""
        return self._labels

    @labels.setter
    def labels(self, value: Sequence[str]):
        self._set_param("labels", list(value))
        self._set_labels(value)

    def _label_names(self):
        return set(self._param("labels", None) or ())

    def _inputs(self) -> Inputs:
        return Inputs(points_input("skeleton", self._labels, "joint positions", accepts=(dict,)))

    def _schema(self) -> Schema:
        return Schema(Output("noise", kind=bool, doc="motion judged random"))

    def _process(self, frame: Any, timestamp: Optional[float]) -> Result:
        if (problem := self._label_problem(frame, timestamp)) is not None:
            return problem
        points = labelled_set(frame, self._labels, "MotionNoiseDetector")
        if reason := non_finite(list(points.values()), allow_empty=True):
            return self.no_output(Status.INVALID_INPUT, reason, timestamp)
        return self._to_result(self._block.process(points, self._time_step(timestamp)), timestamp)

    def _to_result(self, raw: bool, timestamp: Optional[float]) -> Result:
        return self.result(noise=raw, timestamp=timestamp)


__all__ = ["MotionNoiseDetector"]
