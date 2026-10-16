"""Kinetic energy of a skeleton: the weighted sum of the squared speeds of its joints.

Skeleton frames are ``(N, 3)`` arrays or dicts ``label -> (x, y, z)``. The feature declares its outputs as a ``Schema``
(``feature.outputs``) and returns a ``Result`` (see ``pyeyesweb.data_models``). Timestamps are optional and in seconds.
"""

from typing import Any, Mapping, Optional, Sequence

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


def _weights_by_label(weights: Any, labels: Optional[Sequence[str]]) -> dict:
    """A sequence of weights, one per label, as the mapping the block takes; anything else raises here, not in the core."""
    if labels is None or isinstance(weights, (str, bytes)) or not hasattr(weights, "__len__"):
        raise ValueError("KineticEnergy: weights must be a mapping joint -> weight, or a sequence with one weight per label "
                         f"(given with labels= or skeleton=), got {type(weights).__name__}")
    if len(weights) != len(labels):
        raise ValueError(f"KineticEnergy: weights has {len(weights)} value{'' if len(weights) == 1 else 's'}, "
                         f"the skeleton has {len(labels)} joints")
    return dict(zip(labels, weights))


@describe(Layer.LOW_LEVEL, eyesweb="KineticEnergyIndex (KineticEnergy)")
class KineticEnergy(LabelGuard, FrameFeature):
    r"""Weighted kinetic energy of a set of labelled 3D points, such as the joints of a skeleton.

    The kinetic energy of the body is the amount of motion it carries, with fast and heavy segments counting more.
    In ``"position"`` mode (default) the speed :math:`\mathbf{v}_i` of joint :math:`i` is the displacement between
    two consecutive frames divided by the time step; in ``"velocity"`` mode the frames already hold the velocities.
    With :math:`w_i` the weight of the joint (an approximation of its mass),

    .. math::

        E = \frac{1}{2} \sum_{i} w_i \, \lVert \mathbf{v}_i \rVert^2 .

    Only the joints listed in ``weights`` contribute. If ``reference_point`` names a joint, the positions are taken
    relative to it (position mode), so that the translation of the whole body does not count. The time step of a call
    is the difference to the previous ``timestamp`` if given, else ``1 / sampling_rate``, else one second per frame.

    Parameters
    ----------
    labels : sequence of str, optional
        Joint names, in the order of the rows of an array frame. Needed for array input; a dict frame carries its own
        names. Taken from ``skeleton`` when that is given.
    skeleton : str or Skeleton, optional
        A skeleton preset (``"kinect_v2"``, ...) or definition. It sets ``labels`` and ``weights`` (the preset
        weights, or 1.0 for every joint where a preset defines none).
    input_mode : {"position", "velocity"}, optional
        ``"position"`` (default): the frames hold positions and the feature differentiates them; the first frame gives
        0. ``"velocity"``: the frames hold velocities and the feature applies the formula directly (no time step, no
        ``reference_point``). This mode is an extension: EyesWeb takes positions only.
        ``KineticEnergy.from_position(...)`` and ``KineticEnergy.from_velocity(...)`` build one or the other.
        *(structural)*
    weights : mapping of str to float or sequence of float, optional
        Weight :math:`w_i` of each joint (dimensionless, or a mass in the unit of your choice; the energy is in that
        unit times the squared speed). A mapping ``joint -> weight`` or a sequence with one weight per label (a
        different length raises ``ValueError``). Needed unless ``skeleton`` is given. *(live)*
    reference_point : str, optional
        Joint the positions are taken relative to, in position mode. Defaults to ``""`` (none). *(live)*
    sampling_rate : float, optional
        Sampling rate of the frames in Hz, used when no timestamp is given. Defaults to ``None`` (one second per
        frame, and the ``reason`` says so). *(live)*

    Notes
    -----
    **Inputs.** One skeleton frame per call: an ``(N, 3)`` array in the order of ``labels`` or a dict
    ``label -> (x, y, z)``. ``process(frame, *, timestamp=None)``; ``run(frames, *, timestamps=None)`` takes a
    ``(T, N, 3)`` recording. ``timestamp`` is in seconds.

    **Outputs.** ``kinetic_energy``: non-negative scalar, in ``weights`` times (length/s)^2 (length per frame in
    position mode without a time).

    **Statuses.** ``OK`` from the first frame (the first frame of position mode gives 0, there is no previous frame);
    ``INVALID_INPUT`` when the frame holds NaN or infinity, is empty, is a dict that lacks a weighted joint
    (``"missing joints: ..."``), or the timestamp does not increase. A rejected frame is not taken as the
    previous one: the next step is measured from the last valid frame.

    Limitations: the weights are a weighting of the joints, not a body model; the presets without anthropometric
    weights (``qualisys_sport``, ``mediapipe``, ``openpose``) weight every joint by 1.0.

    References
    ----------
    :cite:`glowinski2011minimal`, :cite:`camurri2003recognizing`

    Examples
    --------
    >>> import numpy as np
    >>> from pyeyesweb.low_level import KineticEnergy
    >>> frames = np.zeros((3, 2, 3))
    >>> frames[:, 0, 0] = [0.0, 0.1, 0.2]  # joint 0 moves at 1 m/s
    >>> frames[:, 1, 1] = [0.0, 0.2, 0.4]  # joint 1 moves at 2 m/s
    >>> feature = KineticEnergy(labels=["hand", "elbow"], weights={"hand": 1.0, "elbow": 2.0}, sampling_rate=10.0)
    >>> feature.run(frames).kinetic_energy.round(3)
    array([0. , 4.5, 4.5])
    """
    _core_class = core.motion.KineticEnergyIndex
    _timed = True

    def __init__(self, labels: Optional[Sequence[str]] = None, skeleton: Any = None, **params: Any):
        labels, params = with_skeleton(skeleton, labels, params, lambda resolved: {"weights": resolved.weights_or_uniform()})
        if params.get("weights") is not None and not isinstance(params["weights"], Mapping):
            params["weights"] = _weights_by_label(params["weights"], labels)
        super().__init__(**params)
        self._set_labels(labels)
        self._layout = None if labels is None else core.SkeletonLayout(list(labels))

    @input_mode_factory("position")
    def from_position(cls) -> "KineticEnergy":
        """Kinetic energy of joint positions (the EyesWeb mode).

        Each frame holds the positions ``(N, 3)`` of the joints, or a dict ``label -> (x, y, z)``. Stateful: the speed is
        the difference to the previous frame over the time step, so the first frame gives 0. Takes the parameters of
        ``KineticEnergy`` except ``input_mode``.
        """

    @input_mode_factory("velocity")
    def from_velocity(cls) -> "KineticEnergy":
        """Kinetic energy of joint velocities (an extension, not in EyesWeb).

        Each frame holds the velocities ``(N, 3)`` of the joints, or a dict ``label -> (vx, vy, vz)``. Stateless:
        ``0.5 * w * |v|^2`` per frame from the first one on, with no time step and no ``reference_point``. Takes the
        parameters of ``KineticEnergy`` except ``input_mode``.
        """

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
        stamps = None if timestamps is None else np.asarray(timestamps, dtype=float)
        if not np.isfinite(data).all() or (stamps is not None and not (np.isfinite(stamps).all() and (np.diff(stamps) > 0).all())):
            return super().run(data, timestamps=timestamps, reset=reset)  # rows the central rules reject: the loop of `process`
        if reset:
            self.reset()
        self._check_recording([data])
        steps = np.array([self._time_step(timestamp) for timestamp in ([None] * len(data) if stamps is None else stamps)])
        energy = self._block.run(self._need_layout(), data, steps)
        return Recorder.from_arrays(self, {"kinetic_energy": energy}, timestamps=timestamps)

    def _need_layout(self):
        if self._layout is None:
            raise ValueError("array input needs the joint names: construct with KineticEnergy(labels=[...])")
        return self._layout


__all__ = ["KineticEnergy"]
