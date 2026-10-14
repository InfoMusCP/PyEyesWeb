"""Kinetic energy (EyesWeb KineticEnergy).

Skeletons are dicts `label -> (x, y, z)`. The feature declares its outputs as a `Schema` (`feature.outputs`) and
returns a `Result` (see `pyeyesweb.data_models`). Timestamps are optional and in seconds.
"""

from typing import Any, Optional, Sequence

import numpy as np

from pyeyesweb._core import core
from pyeyesweb.base.core_feature import FrameFeature
from pyeyesweb.catalog import Layer, describe
from pyeyesweb.base.inputs import non_finite, points_input
from pyeyesweb.base.signatures import input_mode_factory
from pyeyesweb.data_models.inputs import Inputs
from pyeyesweb.data_models.recorder import Recorder
from pyeyesweb.data_models.results import Output, Result, Schema, Status
from pyeyesweb.base.labels import LabelGuard
from pyeyesweb.skeletons import with_skeleton


@describe(Layer.LOW_LEVEL, eyesweb="KineticEnergyIndex (KineticEnergy)")
class KineticEnergy(LabelGuard, FrameFeature):
    """Kinetic energy of labelled 3D points (EyesWeb KineticEnergy).

    Input: one skeleton frame per call, an `(N, 3)` array in the order of `labels`, or a dict `label -> (x, y, z)`.
    `process(frame, timestamp=None)` returns `kinetic_energy`, the weighted kinetic energy of the skeleton (0 on the first
    frame in `POSITION` mode). `run(frames, timestamps=None)` processes a whole `(T, N, 3)` recording in C++.

    `labels` are the joint names of the arrays; they are needed for array input (a dict carries its own).
    `input_mode` (EXTENSION, not in EyesWeb): `"position"` (default, faithful) takes positions and differentiates
    them; `"velocity"` takes velocities and applies 0.5 * w * |v|^2 directly. `KineticEnergy.from_position(...)` and
    `KineticEnergy.from_velocity(...)` build one or the other; they take the constructor's parameters.
    `INVALID_INPUT` for NaN or infinity, an empty frame or ("missing joints: ...") a dict frame that lacks a weighted joint;
    `timestamp` is the timestamp in seconds (`NaN` when not given).
    """
    _core_class = core.motion.KineticEnergyIndex
    _timed = True

    def __init__(self, labels: Optional[Sequence[str]] = None, skeleton: Any = None, **params: Any):
        labels, params = with_skeleton(skeleton, labels, params, lambda resolved: {"weights": resolved.weights_or_uniform()})
        super().__init__(**params)
        self._set_labels(labels)
        self._layout = None if labels is None else core.SkeletonLayout(list(labels))

    @input_mode_factory("position")
    def from_position(cls) -> "KineticEnergy":
        """Kinetic energy of joint positions (the faithful mode): each frame holds the positions `(N, 3)` of the joints, or a
        dict `label -> (x, y, z)`. Stateful: the speed is the difference to the previous frame over the time step, so
        the first frame gives 0. Takes the parameters of `KineticEnergy` except `input_mode`."""

    @input_mode_factory("velocity")
    def from_velocity(cls) -> "KineticEnergy":
        """Kinetic energy of joint velocities (EXTENSION): each frame holds the velocities `(N, 3)` of the joints, or a dict
        `label -> (vx, vy, vz)`. Stateless: 0.5 * w * |v|^2 per frame from the first one on, with no time step and no
        `reference_point`. Takes the parameters of `KineticEnergy` except `input_mode`."""

    def _label_names(self):
        return set(self._param("weights", None) or ())

    def _inputs(self) -> Inputs:
        return Inputs(points_input("skeleton", self._labels, "joint positions or velocities", accepts=(dict,)))

    def _schema(self) -> Schema:
        return Schema(Output("kinetic_energy", unit="<length>^2/s^2", doc="weighted kinetic energy of the skeleton"))

    def _process(self, frame: Any, timestamp: Optional[float]) -> Result:
        if isinstance(frame, dict):
            raw = self._block.process(frame, self._time_step(timestamp))
        else:
            points = np.asarray(frame, dtype=float)
            if reason := non_finite(points):  # an invalid frame takes no time: the next step is measured from the last valid one
                return self._no_output(Status.INVALID_INPUT, reason, timestamp)
            raw = self._block.process_array(self._need_layout(), points, self._time_step(timestamp))
        return self._to_result(raw, timestamp)

    def _to_result(self, raw: float, timestamp: Optional[float]) -> Result:
        return self._finite_result(kinetic_energy=raw, timestamp=timestamp)

    def run(self, data: Any, *, timestamps: Optional[Any] = None, reset: bool = True) -> Recorder:
        data = np.asarray(data, dtype=float)
        if not np.isfinite(data).all() or (timestamps is not None and not (np.diff(np.asarray(timestamps, dtype=float)) > 0).all()):
            return super().run(data, timestamps=timestamps, reset=reset)  # rows the central rules reject: the loop of `process`
        if reset:
            self.reset()
        self._check_recording([data])
        stamps = [None] * len(data) if timestamps is None else np.asarray(timestamps, dtype=float)
        energy = self._block.run(self._need_layout(), data, np.array([self._time_step(timestamp) for timestamp in stamps]))
        return Recorder.from_arrays(self.outputs, {"kinetic_energy": energy}, timestamps=timestamps)

    def _need_layout(self):
        if self._layout is None:
            raise ValueError("array input needs the joint names: construct with KineticEnergy(labels=[...])")
        return self._layout


__all__ = ["KineticEnergy"]
