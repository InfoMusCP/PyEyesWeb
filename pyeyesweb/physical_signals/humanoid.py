"""Mass-spring models of a body (EyesWeb HumanoidModel catalog): virtual sensors that turn a captured skeleton into a
physically simulated one, into bone directions or into a prediction.

* :class:`HumanoidSimulator`, :class:`HumanoidOrientations`: a fixed 21-joint humanoid (the joints of the Kinect SDK v1
  as EyesWeb names them); ``HUMANOID_JOINTS`` and ``HUMANOID_BONES`` list its joint and bone names.
* :class:`GenericModelOrientations`, :class:`GenericModelSimulator`, :class:`GenericModelPredictor`,
  :class:`GenericModelEstimator`: the same features for a model of your own, a :class:`MassSpringModel` (also loaded
  from an EyesWeb XML file). Positions are in the unit of the model.
* :class:`PointsPredictor`: one-step linear extrapolation of any labelled points.

A frame is a dict ``label -> (x, y, z)`` or an ``(N, 3)`` array in the order of ``labels``. The model has its own joint
names; ``joint_map`` maps each of them to the label of your data (``{"head": "Head", ...}``; the names you do not list
keep their own name) and the constructor raises when the labels do not hold a joint the model needs. A joint that is
missing in a frame (absent from the dict, or a row with a NaN) is a dropout the model handles (its bones stay as they
were); infinite values and a frame without any joint are ``INVALID_INPUT``. Outputs are labelled by the names of the
model.

Time: the simulators, the predictor and the estimator advance the model by the time step of the call in seconds (the
library rule: ``timestamp``, else ``sampling_rate`` in Hz, default ``None``, else 1 s per call and the ``reason`` says
``"no time given: per-sample derivatives"``).

Units: ``units="m"|"mm"`` (default ``"m"``) is the unit of your frames, of ``gravity`` / ``floor_position`` and of the
outputs. :class:`HumanoidSimulator` works internally in millimetres (the EyesWeb body is defined in mm) and converts at
the boundary, the one place where the library rescales data; the generic models run in the unit of their own model and
``units`` names it (stiffness and damping are in that unit).

Known limitation of the simulators: the rotation springs make chains of four or five bones flutter at a low ``damping``
and the model is not a noise filter; the default ``damping=10`` (EyesWeb: 0.3, which diverges) is stable, 3 follows
clean data with less lag.
"""

import math
import os
from typing import Any, Dict, Mapping, Optional, Sequence, Tuple, Union

import numpy as np

from pyeyesweb._core import core
from pyeyesweb.base.core_feature import XYZ, CoreFeature, FrameFeature
from pyeyesweb.base.inputs import points_input
from pyeyesweb.catalog import Layer, describe
from pyeyesweb.data_models.inputs import Input, InputKind, Inputs
from pyeyesweb.data_models.results import Output, Result, Schema, Status
from pyeyesweb.base.labels import LabelGuard
from pyeyesweb.physical_signals._humanoid_model import (
    HUMANOID_BONES, HUMANOID_JOINTS, NAME_PARAMS, MassSpringModel, core_model
)
from pyeyesweb.skeletons import with_skeleton

_humanoid = core.humanoid

_NAN_POINT = (math.nan,) * 3


def _check_rate(sampling_rate: Optional[float]) -> None:
    if sampling_rate is not None and not (isinstance(sampling_rate, (int, float)) and not isinstance(sampling_rate, bool)
                                          and math.isfinite(sampling_rate) and sampling_rate > 0):
        raise ValueError(f"sampling_rate must be a positive number of Hz or None, got {sampling_rate!r}")


def _switch(name: str, value: Any) -> bool:
    if not isinstance(value, bool):
        raise TypeError(f"{name} must be True or False, got {value!r}")
    return value


class _ModelInput(LabelGuard):
    """Mixin: the frames of the user, with their own labels, become the frames of the model (`names` of the model, in
    its order); `_input_names()` gives the names the input must hold."""

    _labels: Optional[Tuple[str, ...]] = None
    _dropouts = True  # missing joints and NaN rows are dropouts of the model, not bad data
    _given_map: Mapping[str, str] = {}
    _core_names = {"reference_direction": "ref_dir"}

    def _input_names(self) -> Tuple[str, ...]:
        raise NotImplementedError

    def _mapping(self, names: Optional[Sequence[str]] = None) -> Dict[str, str]:
        """`model name -> label of the user's data`, the names not in `joint_map` keeping their own."""
        return {name: self._given_map.get(name, name) for name in (self._input_names() if names is None else names)}

    def _label_names(self) -> set:
        return set(self._mapping().values())

    def _set_input(self, labels: Optional[Sequence[str]], joint_map: Optional[Mapping[str, str]],
                   names: Optional[Sequence[str]] = None) -> None:
        """Take `labels` and `joint_map` after checking them against the model names; nothing changes on an error."""
        names = tuple(self._input_names() if names is None else names)
        given = dict(joint_map or {})
        owner = type(self).__name__
        if unknown := sorted(set(given) - set(names)):
            raise ValueError(f"{owner}: joint_map names that are not model names: {unknown}; the model has {list(names)}")
        labels = None if labels is None else tuple(labels)
        if labels is not None:
            wanted = {name: given.get(name, name) for name in names}
            if missing := {name: label for name, label in wanted.items() if label not in labels}:
                raise ValueError(f"{owner}: labels do not contain {sorted(missing.values())}, which the model reads as "
                                 f"{sorted(missing)}; map the model names to your labels with joint_map=")
        self._labels, self._given_map = labels, given
        self._outputs_changed()

    @property
    def labels(self) -> Optional[Tuple[str, ...]]:
        """Names of the rows of array frames; `None`: the rows are in the order of the model names (`inputs`)."""
        return self._labels

    @labels.setter
    def labels(self, value: Optional[Sequence[str]]) -> None:
        self._set_input(value, self._given_map)

    @property
    def joint_map(self) -> Dict[str, str]:
        """Model name -> label of the data, for the names that differ."""
        return dict(self._given_map)

    @joint_map.setter
    def joint_map(self, value: Optional[Mapping[str, str]]) -> None:
        self._set_input(self._labels, value)

    def _outputs_changed(self) -> None:
        self.__dict__.pop("_row_cache", None)
        super()._outputs_changed()

    def _rows(self) -> Optional[np.ndarray]:
        """Row of each model name in an array frame, `None` when the frame is in the order of the model names."""
        if self._labels is None:
            return None
        rows = self.__dict__.get("_row_cache")
        if rows is None:
            mapping = self._mapping()
            rows = self.__dict__["_row_cache"] = np.array([self._labels.index(mapping[name]) for name in mapping])
        return rows

    def _frame_input(self, name: str, doc: str) -> Input:
        names = self._input_names()
        return points_input(name, self._labels if self._labels is not None else names, doc, accepts=(dict,),
                            allow_non_finite=True)

    def _points(self, frame: Any, timestamp: Optional[float]) -> Union[np.ndarray, Result]:
        """The frame as the `(len(names), 3)` array of the model (NaN rows for the missing points), or the
        `INVALID_INPUT` result."""
        if isinstance(frame, dict):
            if (problem := self._label_problem(frame, timestamp)) is not None:
                return problem
            points = np.full((len(self._input_names()), 3), math.nan)
            for row, label in enumerate(self._mapping().values()):
                if label in frame:
                    points[row] = frame[label]
        else:
            points = np.asarray(frame, dtype=float)
            if points.size == 0:
                return self._no_output(Status.INVALID_INPUT, "empty frame", timestamp)
            rows = self._rows()
            points = np.ascontiguousarray(points if rows is None else points[rows])
        if np.isinf(points).any():
            return self._no_output(Status.INVALID_INPUT, "infinite values", timestamp)
        if np.isnan(points).all():
            return self._no_output(Status.INVALID_INPUT, "no joint present in the frame", timestamp)
        return points


class _Timed:
    """Mixin of the blocks that advance a model by the time step of each call: the library rule of `CoreFeature` (the
    timestamp, else `sampling_rate` Hz, default None, else 1 s per call with the per-sample note in `reason`)."""

    _timed = True

    def _set_param(self, name: str, value: Any) -> None:
        if name == "sampling_rate":
            _check_rate(value)
        super()._set_param(name, value)


class _Units:
    """Mixin of the features with length-valued parameters (`gravity`, `floor_position`): `units="m"|"mm"` (default
    "m") is the unit of the data, of those parameters and of the outputs. The block gets them in `_core_factor`
    units of its own: see `_block_params`."""

    _unit_params = {"gravity": 1, "floor_position": 1}
    _internal_mm = False

    def _block_params(self, params: dict) -> dict:
        # The shared mechanism scales metres to the data unit (m -> 1, mm -> 1000). The humanoid core works in mm
        # whatever the data is, so its parameters go from the data unit to mm (m -> 1000, mm -> 1): the same
        # mechanism with the unit flipped. The generic models run in the unit of their own model: no scaling.
        units = params.get("units", "m")
        flipped = {"m": "mm", "mm": "m"}[units] if self._internal_mm else "m"
        return super()._block_params({**params, "units": flipped})

    @property
    def _to_core(self) -> float:
        """Millimetres in one data unit for the features that run in mm; 1 for the others."""
        return 1000.0 if self._internal_mm and self._params.get("units", "m") == "m" else 1.0

    def _units_output(self) -> str:
        return self._params["units"]


class _Simulator(_Timed):
    """Mixin of the simulators: `start_from_input` puts the model on the first frame instead of letting it settle there
    from its rest pose."""

    _fresh = True
    _start_from_input = False

    @property
    def start_from_input(self) -> bool:
        """Whether the first frame after construction or `reset()` is put on the input (EyesWeb's reset trigger: the
        present joints take the input position and the rest lengths become the input bone lengths) and returned as it
        is. A change applies from the next `reset()`."""
        return self._start_from_input

    @start_from_input.setter
    def start_from_input(self, value: bool) -> None:
        self._start_from_input = _switch("start_from_input", value)

    def _teleport(self) -> bool:
        teleport = self._start_from_input and self._fresh
        self._fresh = False
        return teleport

    def reset(self) -> None:
        self._fresh = True
        super().reset()


class _ModelFeature(_ModelInput):
    """Mixin of the features built on a `MassSpringModel`: `model`, which is a parameter like the others (structural)."""

    @classmethod
    def _coerce_choices(cls, params: dict) -> dict:
        out = super()._coerce_choices(params)
        if "model" in out:
            out["model"] = core_model(out["model"])
        return out

    @staticmethod
    def _names_of(model: Any) -> Tuple[str, ...]:
        raise NotImplementedError

    def _input_names(self) -> Tuple[str, ...]:
        return self._names_of(self._params["model"])

    @property
    def model(self) -> MassSpringModel:
        """A copy of the model in its current state (an estimator: with the estimated parameters). Setting it changes
        the model; the state restarts and the labels are checked against the new names."""
        block_model = getattr(self._block, "model", None)
        return MassSpringModel._wrap(self._params["model"] if block_model is None else block_model)

    @model.setter
    def model(self, value: Any) -> None:
        model = core_model(value)
        self._set_input(self._labels, self._given_map, self._names_of(model))  # checks before anything changes
        try:
            self._set_param("model", model)
        except Exception:
            self._set_input(self._labels, self._given_map)
            raise

    def _output_labels(self) -> Tuple[str, ...]:
        return tuple(self._block.output_labels)

    def _positions_output(self) -> Output:
        return Output("positions", (len(self._output_labels()), 3), labels=self._output_labels(), components=XYZ,
                      unit=self._params["units"], doc="positions of the masses of the model, in `units`")


# ---------------------------------------------------------------------------------------------------------------------
# the humanoid


@describe(Layer.PHYSICAL_SIGNALS, eyesweb="HumanoidSimulator (MassSpringHumanoidSimulator)")
class HumanoidSimulator(_Units, _Simulator, _ModelInput, CoreFeature):
    """A physically based humanoid that follows a captured skeleton.

    The captured joints are replaced by the pose of a virtual body: a humanoid of 21 masses (the joints of
    ``HUMANOID_JOINTS``) joined by 20 springs (the bones of ``HUMANOID_BONES``) is integrated in time. Every bone is a
    spring with a length force, which keeps its rest length, and a rotation force, which turns it towards the direction
    observed in the input; the head is the (very heavy) root. The simulated pose is smooth and always articulated, with the
    proportions of the model body, so the feature acts as a virtual sensor that removes the jitter and the dropouts of a
    captured skeleton and yields a physically plausible joint trajectory. It is not a noise filter in the
    signal-processing sense (see Notes).

    ``process(skeleton, control=None, *, timestamp=None)`` takes the captured joints, a dict ``label -> (x, y, z)`` or a
    ``(21, 3)`` array in the order of ``labels``. The optional ``control`` holds bone directions, a ``(20, 3)`` array in the
    order of ``HUMANOID_BONES`` or a dict ``"<joint1>-<joint2>" -> (x, y, z)``; the bones then follow them instead of the
    directions seen in the joints. They are directions *relative to the parent bone*, the convention of the output of
    :class:`HumanoidOrientations`: passing that output as ``control`` reproduces the pose of the joints it came from.

    Parameters
    ----------
    labels : sequence of str, optional
        Names of the rows of array frames *(live)*. Default ``None``: the rows follow the order of ``HUMANOID_JOINTS``.
    joint_map : dict, optional
        ``joint of the model -> label of your data`` *(live)*; the model names are those of ``HUMANOID_JOINTS`` and the
        names you leave out keep their own. The constructor raises ``ValueError`` when ``labels`` lack a joint the model
        needs.
    start_from_input : bool, default False
        Put the model on the first frame after construction or ``reset()`` instead of letting it settle there from its
        T-pose *(live)*. The present joints take the input positions, the rest lengths of the bones become the bone
        lengths of the input, and that first frame is returned as it is. A change applies from the next ``reset()``.
    reference_direction : tuple of float, default (1.0, 0.0, 0.0)
        Reference direction of the model *(live)*: the direction from which the rest directions of the springs are
        measured (dimensionless; the x axis by default).
    integration_step : float, default 0.001
        Step of the numerical integration in seconds, > 0 *(live)*. A call that advances the model by ``dt`` seconds runs
        ``int(dt / integration_step)`` steps.
    gravity : tuple of float, default (0.0, 0.0, 0.0)
        Gravity vector in ``units`` per second squared *(live)*; zero means no gravity.
    damping : float, default 10.0
        Damping coefficient of the springs *(live)*. The EyesWeb default, 0.3, makes chains of four or five bones diverge;
        10 is stable with noisy input and 3 follows clean data with less lag.
    viscosity : float, default 0.0
        Viscous friction of the masses *(live)*.
    length_forces : bool, default True
        Switch on the forces that keep each spring at its rest length *(live)*.
    rotation_forces : bool, default True
        Switch on the forces that turn each spring towards its target direction *(live)*.
    ground_interaction : bool, default False
        Add a floor, the plane through ``floor_position`` whose normal is opposite to gravity *(live)*; a mass below it is
        pushed back along the normal.
    floor_position : tuple of float, default (0.0, 0.0, 0.0)
        A point of the floor plane, in ``units`` *(live)*.
    sampling_rate : float, optional
        Frame rate in Hz, used for the time step of a call that has no ``timestamp`` *(live)*. Default ``None`` (no
        hidden rate): the step is then 1 s and ``reason`` says ``"no time given: per-sample derivatives"``.
    units : {"m", "mm"}, default "m"
        Unit of your frames, of the outputs, of ``gravity`` and of ``floor_position`` *(live)*. See Notes.

    Notes
    -----
    **Outputs.** ``joints``: ``(21, 3)`` array of ``(x, y, z)`` in ``units``, labelled by ``HUMANOID_JOINTS``; a joint
    the model did not produce is NaN. The result is ``OK`` on every valid call (there is no warm-up). A frame with an infinite value, an empty frame, a frame without any joint (every row NaN) and a dict frame
    whose keys match none of the names the model reads are ``INVALID_INPUT`` (the cause is in ``result.reason``); a joint
    that is missing (absent from the dict, or a row with a NaN) is a dropout the model handles.

    **Time.** The time step of a call is ``timestamp - previous timestamp`` in seconds, else ``1 / sampling_rate``, else 1 s. A
    timestamp that does not increase gives ``INVALID_INPUT`` (``"non-increasing timestamp"``) and leaves the model where it
    was; a non-finite timestamp raises ``ValueError``. The first timed call after construction or ``reset()`` uses
    ``1 / sampling_rate`` (or 1 s), never the absolute time.

    **Units.** This is the one feature that rescales data. The EyesWeb body is defined in millimetres and the spring forces
    depend on the length unit, so the feature works internally in millimetres and converts at the boundary: with
    ``units="m"`` frames are multiplied by 1000 on the way in and joints divided by 1000 on the way out, with ``"mm"``
    nothing is converted. A body driven in metres reproduces the millimetre run up to rounding; metres declared as
    ``"mm"`` give a different motion, because the model is not scale free.

    **Behaviour.** The head is pinned: the output is the pose of a body hanging from where its head starts, the T-pose at
    the origin or, with ``start_from_input``, the first frame; the translation of the person is not followed, as in
    EyesWeb. Bone lengths stay those of the body and only the directions follow the input. A joint missing in a frame
    leaves its bones unchanged. Every parameter is live; ``reset()`` puts the body back in the T-pose.

    **Known limitation.** The rotation springs make chains of four or five bones flutter at a low ``damping``, and the
    model is not a noise filter: it follows the input with a lag that grows with ``damping``.

    **Differences from EyesWeb.** The default ``damping`` is 10 (EyesWeb: 0.3, which diverges); time is in seconds per
    call; ``control`` is read as directions relative to the parent bone (EyesWeb read world directions, so there the output
    of its orientation extractor gave another pose).

    **Corrected in the core.** The damping force is proportional to the relative velocity of the two masses (the original
    used speed magnitudes and injected energy); the feet of the T-pose are built along the direction they rest in, so the
    body at rest is in equilibrium; the reset to the input, which the original could never reach, works and moves only the
    joints that are present.

    Examples
    --------
    >>> import numpy as np
    >>> from pyeyesweb.physical_signals import HumanoidSimulator
    >>> simulator = HumanoidSimulator(sampling_rate=25.0)
    >>> result = simulator.process({"head": (0.0, 1.7, 0.0)})    # a lone joint: the body hangs from it, in its T-pose
    >>> result.joints.shape
    (21, 3)
    >>> follower = HumanoidSimulator(sampling_rate=25.0, start_from_input=True)
    >>> bool(np.allclose(follower.process(result.joints).joints, result.joints))
    True
    """
    _core_class = _humanoid.HumanoidSimulator
    _hidden_params = NAME_PARAMS
    _internal_mm = True

    def __init__(self, labels: Optional[Sequence[str]] = None, joint_map: Optional[Mapping[str, str]] = None,
                 *, start_from_input: bool = False, **params: Any):
        _check_rate(params.get("sampling_rate"))
        self._start_from_input = _switch("start_from_input", start_from_input)
        super().__init__(**params)
        self._set_input(labels, joint_map)
        self._layout = core.SkeletonLayout(list(HUMANOID_JOINTS))

    def _input_names(self) -> Tuple[str, ...]:
        return HUMANOID_JOINTS

    def _inputs(self) -> Inputs:
        return Inputs(self._frame_input("skeleton", "captured joints, in `units`"),
                      Input("control", InputKind.POINTS, (len(HUMANOID_BONES), 3), HUMANOID_BONES, doc=(
                          "bone directions relative to the parent bone (the output of HumanoidOrientations) replacing those seen in the joints"), accepts=(dict,), optional=True,
                            allow_non_finite=True))

    def _schema(self) -> Schema:
        return Schema(Output("joints", (len(HUMANOID_JOINTS), 3), labels=HUMANOID_JOINTS, components=XYZ,
                             unit=self._units_output(), doc="simulated joint positions"))

    def process(self, skeleton: Any, control: Any = None, *, timestamp: Optional[float] = None) -> Result:
        points = self._points(skeleton, timestamp)
        if isinstance(points, Result):
            return points
        step = self._time_step(timestamp)
        teleport = self._teleport()
        scale = self._to_core
        if scale != 1.0:  # metres in, the core works in mm
            points = points * scale
        if control is None:
            raw = self._block.process_array(self._layout, points, step, teleport)
        else:
            raw = self._with_control(points, control, step, teleport)
        if scale != 1.0:
            raw = raw / scale
        return self._result(joints=raw, timestamp=timestamp)

    def _with_control(self, points: np.ndarray, control: Any, step: float, teleport: bool) -> np.ndarray:
        joints = {name: tuple(row) for name, row in zip(HUMANOID_JOINTS, points.tolist()) if not np.isnan(row).any()}
        if not isinstance(control, dict):
            control = dict(zip(HUMANOID_BONES, np.asarray(control, dtype=float).tolist()))
        directions = {name: tuple(vector) for name, vector in control.items() if np.isfinite(vector).all()}
        out = self._block.process(joints, step, directions, teleport)
        return np.array([out.get(name, _NAN_POINT) for name in self._block.output_labels])


@describe(Layer.PHYSICAL_SIGNALS, eyesweb="HumanoidOrientationsExtractor")
class HumanoidOrientations(_ModelInput, FrameFeature):
    """The orientation of every bone of a skeleton relative to its parent bone.

    A posture is described by the direction of each of the 20 bones of ``HUMANOID_BONES`` (named
    ``"<joint1>-<joint2>"``) expressed in the frame of the previous bone of the chain, so that the description does not
    depend on where the body is or how its parent segments are oriented. The output is the convention of the ``control``
    input of :class:`HumanoidSimulator`, which takes it as it is.

    ``process(skeleton, *, timestamp=None)`` takes the captured joints, a dict ``label -> (x, y, z)`` or a ``(21, 3)`` array
    in the order of ``labels``. The feature is stateful (``reset()``) but has no time axis: ``timestamp`` is only copied
    into ``result.timestamp``.

    Parameters
    ----------
    labels : sequence of str, optional
        Names of the rows of array frames *(live)*. Default ``None``: the rows follow the order of ``HUMANOID_JOINTS``.
    joint_map : dict, optional
        ``joint of the model -> label of your data`` *(live)*, as in :class:`HumanoidSimulator`; names left out keep their
        own.
    reference_direction : tuple of float, default (1.0, 0.0, 0.0)
        Reference direction of the root bones (dimensionless; the x axis by default) *(structural)*: the rotation of a
        root bone is the shortest arc from this direction.

    Notes
    -----
    **Outputs.** ``directions``: ``(20, 3)`` array of unit vectors, dimensionless, labelled by ``HUMANOID_BONES``. A
    bone of zero length gives the zero vector. A joint missing in a frame keeps the position it had in the previous frame
    (the T-pose before the first), so a bone whose joint was never seen is still computed. The result is ``OK`` on every
    valid call. A frame with an infinite value, an empty frame, a frame without any joint (every row NaN) and a dict frame
    whose keys match none of the names the model reads are ``INVALID_INPUT`` (the cause is in ``result.reason``); a joint
    that is missing (absent from the dict, or a row with a NaN) is a dropout the model handles.

    Examples
    --------
    >>> import numpy as np
    >>> from pyeyesweb.physical_signals import HumanoidOrientations, HumanoidSimulator
    >>> pose = HumanoidSimulator().process({"head": (0.0, 0.0, 0.0)}).joints    # the T-pose, (21, 3)
    >>> directions = HumanoidOrientations().process(pose).directions
    >>> directions.shape
    (20, 3)
    >>> bool(np.allclose(np.linalg.norm(directions, axis=1), 1.0))
    True
    """
    _core_class = _humanoid.HumanoidOrientationsExtractor
    _hidden_params = NAME_PARAMS

    def __init__(self, labels: Optional[Sequence[str]] = None, joint_map: Optional[Mapping[str, str]] = None,
                 **params: Any):
        super().__init__(**params)
        self._set_input(labels, joint_map)
        self._layout = core.SkeletonLayout(list(HUMANOID_JOINTS))

    def _input_names(self) -> Tuple[str, ...]:
        return HUMANOID_JOINTS

    def _inputs(self) -> Inputs:
        return Inputs(self._frame_input("skeleton", "captured joints"))

    def _schema(self) -> Schema:
        return Schema(Output("directions", (len(HUMANOID_BONES), 3), labels=HUMANOID_BONES, components=XYZ,
                             doc="unit direction of each bone in the frame of its previous bone"))

    def _process(self, frame: Any, timestamp: Optional[float]) -> Result:
        points = self._points(frame, timestamp)
        if isinstance(points, Result):
            return points
        return self._result(directions=self._block.process_array(self._layout, points), timestamp=timestamp)


# ---------------------------------------------------------------------------------------------------------------------
# generic models


class _GenericFeature(_ModelFeature):
    """Mixin of the features of a model of your own: `model` is the first argument and `labels` / `joint_map` follow."""

    def __init__(self, model: Union[MassSpringModel, str, os.PathLike],
                 labels: Optional[Sequence[str]] = None, joint_map: Optional[Mapping[str, str]] = None, **params: Any):
        super().__init__(model=model, **params)
        self._set_input(labels, joint_map)

    def _outputs_changed(self) -> None:
        self.__dict__.pop("_layout", None)
        super()._outputs_changed()

    def _model_layout(self) -> Any:
        layout = self.__dict__.get("_layout")
        if layout is None:
            layout = self.__dict__["_layout"] = core.SkeletonLayout(list(self._input_names()))
        return layout


def _mass_names(model: Any) -> Tuple[str, ...]:
    return tuple(model.mass_names)


def _spring_names(model: Any) -> Tuple[str, ...]:
    return tuple(model.spring_names)


@describe(Layer.PHYSICAL_SIGNALS, eyesweb="GenericModelOrientationsExtractor")
class GenericModelOrientations(_GenericFeature, FrameFeature):
    r"""The bone vectors of a mass-spring model from the positions of its masses.

    For every spring :math:`s` of ``model``, the feature gives the vector from its first mass (the hinge) to its second
    mass (the tip),

    .. math::

        \mathbf{b}_s = \mathbf{p}_{\mathrm{tip}(s)} - \mathbf{p}_{\mathrm{hinge}(s)},

    not normalised and in the unit of the data. It is the front end of :class:`GenericModelSimulator` and
    :class:`GenericModelPredictor`, which take these vectors as the directions the springs have to follow.

    ``process(skeleton, *, timestamp=None)`` takes the positions of the masses, one point per mass of ``model`` named like
    the mass (or mapped with ``joint_map``), as a dict ``label -> (x, y, z)`` or an ``(n_masses, 3)`` array in the order of
    ``labels``. The feature is stateless and has no time axis: ``timestamp`` is only copied into ``result.timestamp``.

    Parameters
    ----------
    model : MassSpringModel or str
        The model, or the path of an EyesWeb XML model file *(structural)*. Only the mass and spring names matter here.
    labels : sequence of str, optional
        Names of the rows of array frames *(live)*. Default ``None``: the rows follow the order of ``model.mass_names``.
    joint_map : dict, optional
        ``mass name of the model -> label of your data`` *(live)*; names left out keep their own.

    Notes
    -----
    **Outputs.** ``directions``: ``(n_springs, 3)`` array of ``(x, y, z)``, in the unit of the data, labelled by the spring
    names of the model. A spring with a missing mass is NaN. The result is ``OK`` on every valid call. A frame with an infinite value, an empty frame, a frame without any joint (every row NaN) and a dict frame
    whose keys match none of the names the model reads are ``INVALID_INPUT`` (the cause is in ``result.reason``); a joint
    that is missing (absent from the dict, or a row with a NaN) is a dropout the model handles.

    Examples
    --------
    >>> from pyeyesweb.physical_signals import GenericModelOrientations, MassSpringModel
    >>> model = MassSpringModel()
    >>> model.add_mass("root", 1e10)
    >>> model.add_mass("tip", 1.0, (1.0, 0.0, 0.0))
    >>> model.add_spring("rod", "root", "tip", 1.0, 100.0, (1.0, 0.0, 0.0), 100.0)
    >>> GenericModelOrientations(model).process([[0.0, 0.0, 0.0], [0.0, 1.0, 0.0]]).directions
    array([[0., 1., 0.]])
    """
    _core_class = _humanoid.GenericModelOrientationsExtractor
    _names_of = staticmethod(_mass_names)

    def _inputs(self) -> Inputs:
        return Inputs(self._frame_input("skeleton", "positions of the masses of the model"))

    def _schema(self) -> Schema:
        labels = self._output_labels()
        return Schema(Output("directions", (len(labels), 3), labels=labels, components=XYZ, unit="<length>",
                             doc="vector from the first to the second mass of each spring"))

    def _process(self, frame: Any, timestamp: Optional[float]) -> Result:
        points = self._points(frame, timestamp)
        if isinstance(points, Result):
            return points
        return self._result(directions=self._block.process_array(self._model_layout(), points), timestamp=timestamp)


class _Directions(_GenericFeature):
    """The input of the simulator and the predictor: one direction per spring of the model."""

    _names_of = staticmethod(_spring_names)

    def _inputs(self) -> Inputs:
        return Inputs(self._frame_input("directions", "bone directions of the springs of the model, e.g. the output of "
                                                      "GenericModelOrientations"))

    def _schema(self) -> Schema:
        return Schema(self._positions_output())


@describe(Layer.PHYSICAL_SIGNALS, eyesweb="GenericModelSimulator")
class GenericModelSimulator(_Units, _Simulator, _Directions, CoreFeature):
    """A mass-spring model that follows bone directions.

    A model of your own, a :class:`MassSpringModel` of masses joined by springs, is integrated in time while each spring is
    pulled towards the direction given in the input. The result is a smooth, always articulated trajectory of the masses of
    the model that follows a captured or generated movement: a virtual sensor for any articulated structure (a limb, a
    puppet, a whole body of your own design).

    ``process(directions, *, timestamp=None)`` takes one direction per spring of ``model`` (a dict ``label -> (x, y, z)``,
    labelled by the spring names or mapped with ``joint_map``, or a ``(n_springs, 3)`` array in the order of ``labels``;
    typically the output of :class:`GenericModelOrientations`) as the rest targets of the springs. It advances the model by
    the time step of the call and returns ``positions``.

    Parameters
    ----------
    model : MassSpringModel or str
        The model, or the path of an EyesWeb XML model file *(structural)*.
    labels : sequence of str, optional
        Names of the rows of array frames *(live)*. Default ``None``: the rows follow the order of ``model.spring_names``.
    joint_map : dict, optional
        ``spring name of the model -> label of your data`` *(live)*; names left out keep their own.
    start_from_input : bool, default False
        Move the tips of the springs onto the input at the first frame after construction or ``reset()`` *(live)*; a
        change applies from the next ``reset()``.
    reference_direction : tuple of float, default (1.0, 0.0, 0.0)
        Reference direction of the model *(live)*: the direction from which the rest directions of the springs are
        measured (dimensionless; the x axis by default).
    integration_step : float, default 0.001
        Step of the numerical integration in seconds, > 0 *(live)*. A call that advances the model by ``dt`` seconds runs
        ``int(dt / integration_step)`` steps.
    gravity : tuple of float, default (0.0, 0.0, 0.0)
        Gravity vector in ``units`` per second squared *(live)*; zero means no gravity.
    damping : float, default 10.0
        Damping coefficient of the springs *(live)*. The EyesWeb default, 0.3, makes chains of four or five bones diverge;
        10 is stable with noisy input and 3 follows clean data with less lag.
    viscosity : float, default 0.0
        Viscous friction of the masses *(live)*.
    length_forces : bool, default True
        Switch on the forces that keep each spring at its rest length *(live)*.
    rotation_forces : bool, default True
        Switch on the forces that turn each spring towards its target direction *(live)*.
    ground_interaction : bool, default False
        Add a floor, the plane through ``floor_position`` whose normal is opposite to gravity *(live)*; a mass below it is
        pushed back along the normal.
    floor_position : tuple of float, default (0.0, 0.0, 0.0)
        A point of the floor plane, in ``units`` *(live)*.
    use_input_lengths : bool, default False
        Take the rest length of each spring from the length of the input vector instead of the length of the model *(live)*.
    sampling_rate : float, optional
        Frame rate in Hz, used for the time step of a call that has no ``timestamp`` *(live)*. Default ``None`` (no
        hidden rate): the step is then 1 s and ``reason`` says ``"no time given: per-sample derivatives"``.
    units : {"m", "mm"}, default "m"
        Name of the unit of the model, of the data, of ``gravity``, ``floor_position`` and of the outputs *(live)*.
        Nothing is rescaled (see Notes).

    Notes
    -----
    **Outputs.** ``positions``: ``(n_masses, 3)`` array of ``(x, y, z)`` in ``units``, labelled by the mass names of the
    model. The result is ``OK`` on every valid call (no warm-up). A direction missing in a frame leaves its spring
    unchanged. A frame with an infinite value, an empty frame, a frame without any joint (every row NaN) and a dict frame
    whose keys match none of the names the model reads are ``INVALID_INPUT`` (the cause is in ``result.reason``); a joint
    that is missing (absent from the dict, or a row with a NaN) is a dropout the model handles.

    **Time.** The time step of a call is ``timestamp - previous timestamp`` in seconds, else ``1 / sampling_rate``, else 1 s. A
    timestamp that does not increase gives ``INVALID_INPUT`` (``"non-increasing timestamp"``) and leaves the model where it
    was; a non-finite timestamp raises ``ValueError``. The first timed call after construction or ``reset()`` uses
    ``1 / sampling_rate`` (or 1 s), never the absolute time.

    **Units.** The model, the data, ``gravity``, ``floor_position`` and the outputs are in one and the same length unit, the
    unit of your model; ``units`` only names it (an EyesWeb XML model is usually in millimetres: ``units="mm"``). Nothing is
    rescaled, so the numbers are identical for ``"m"`` and ``"mm"``. The dynamics are those of the model in its own unit,
    and its stiffness and damping are expressed in that unit too: the same model written in another unit moves
    differently. :class:`HumanoidSimulator` is the exception that does convert.

    **Known limitation.** The rotation springs make chains of four or five bones flutter at a low ``damping``; see
    :class:`HumanoidSimulator`.

    **Corrected in the core.** The damping is proportional to the relative velocity of the two masses (the original
    injected energy); a spring is skipped by the length force only when its direction is the zero vector; after the reset
    to the input the spring directions are refreshed; the zero vector normalises to the zero vector instead of NaN.

    Examples
    --------
    >>> from pyeyesweb.physical_signals import GenericModelSimulator, MassSpringModel
    >>> model = MassSpringModel()
    >>> model.add_mass("root", 1e10)
    >>> model.add_mass("tip", 1.0, (1.0, 0.0, 0.0))
    >>> model.add_spring("rod", "root", "tip", 1.0, 100.0, (1.0, 0.0, 0.0), 100.0)
    >>> simulator = GenericModelSimulator(model, sampling_rate=100.0)
    >>> for _ in range(3):
    ...     result = simulator.process([[0.0, 1.0, 0.0]])    # the rod is asked to point along y
    >>> result.positions[1].round(3)
    array([1.   , 0.042, 0.   ])
    """
    _core_class = _humanoid.GenericModelSimulator

    def __init__(self, model: Union[MassSpringModel, str, os.PathLike],
                 labels: Optional[Sequence[str]] = None, joint_map: Optional[Mapping[str, str]] = None,
                 *, start_from_input: bool = False, **params: Any):
        _check_rate(params.get("sampling_rate"))
        self._start_from_input = _switch("start_from_input", start_from_input)
        super().__init__(model, labels, joint_map, **params)

    def process(self, directions: Any, *, timestamp: Optional[float] = None) -> Result:
        points = self._points(directions, timestamp)
        if isinstance(points, Result):
            return points
        step = self._time_step(timestamp)
        raw = self._block.process_array(self._model_layout(), points, step, reset_to_input=self._teleport())
        return self._result(positions=raw, timestamp=timestamp)


@describe(Layer.PHYSICAL_SIGNALS, eyesweb="GenericModelPredictor")
class GenericModelPredictor(_Units, _Timed, _Directions, CoreFeature):
    """The positions a mass-spring model will have a short time ahead.

    Like :class:`GenericModelSimulator` the model follows the bone directions of each frame. ``positions`` is where its
    masses will be ``prediction_interval`` seconds later when the model is left to move on its own, which gives a
    short-term forecast of the movement of an articulated structure. With ``mode="masses_inertia"`` the masses keep their
    velocity; with ``"directions_linear"`` the bone directions are extrapolated linearly. The state of the model is the one
    of the follower: the prediction does not disturb it.

    ``process(directions, *, timestamp=None)`` takes one direction per spring of ``model`` (a dict or a ``(n_springs, 3)``
    array, typically the output of :class:`GenericModelOrientations`) and returns ``positions``.

    Parameters
    ----------
    model : MassSpringModel or str
        The model, or the path of an EyesWeb XML model file *(structural)*.
    labels : sequence of str, optional
        Names of the rows of array frames *(live)*. Default ``None``: the rows follow the order of ``model.spring_names``.
    joint_map : dict, optional
        ``spring name of the model -> label of your data`` *(live)*; names left out keep their own.
    reference_direction : tuple of float, default (1.0, 0.0, 0.0)
        Reference direction of the model *(live)*: the direction from which the rest directions of the springs are
        measured (dimensionless; the x axis by default).
    integration_step : float, default 0.001
        Step of the numerical integration in seconds, > 0 *(live)*. A call that advances the model by ``dt`` seconds runs
        ``int(dt / integration_step)`` steps.
    gravity : tuple of float, default (0.0, 0.0, 0.0)
        Gravity vector in ``units`` per second squared *(live)*; zero means no gravity.
    damping : float, default 10.0
        Damping coefficient of the springs *(live)*. The EyesWeb default, 0.3, makes chains of four or five bones diverge;
        10 is stable with noisy input and 3 follows clean data with less lag.
    viscosity : float, default 0.0
        Viscous friction of the masses *(live)*.
    length_forces : bool, default True
        Switch on the forces that keep each spring at its rest length *(live)*.
    rotation_forces : bool, default True
        Switch on the forces that turn each spring towards its target direction *(live)*.
    ground_interaction : bool, default False
        Add a floor, the plane through ``floor_position`` whose normal is opposite to gravity *(live)*; a mass below it is
        pushed back along the normal.
    floor_position : tuple of float, default (0.0, 0.0, 0.0)
        A point of the floor plane, in ``units`` *(live)*.
    use_input_lengths : bool, default False
        Take the rest length of each spring from the length of the input vector instead of the length of the model *(live)*.
    prediction_interval : float, default 0.2
        How far ahead to predict, in seconds *(live)*.
    mode : {"masses_inertia", "directions_linear"}, default "masses_inertia"
        How the future is computed *(live)*: ``"masses_inertia"`` lets the masses keep their velocity,
        ``"directions_linear"`` extrapolates the bone directions linearly.
    damping_factor : float, default 1.0
        Factor applied to ``damping`` while predicting (dimensionless) *(live)*.
    viscosity_factor : float, default 1.0
        Factor applied to ``viscosity`` while predicting (dimensionless) *(live)*.
    sampling_rate : float, optional
        Frame rate in Hz, used for the time step of a call that has no ``timestamp`` *(live)*. Default ``None`` (no
        hidden rate): the step is then 1 s and ``reason`` says ``"no time given: per-sample derivatives"``.
    units : {"m", "mm"}, default "m"
        Name of the unit of the model, of the data, of ``gravity``, ``floor_position`` and of the outputs *(live)*; nothing
        is rescaled, as in :class:`GenericModelSimulator`.

    Notes
    -----
    **Outputs.** ``positions``: ``(n_masses, 3)`` array of ``(x, y, z)`` in ``units``, the predicted positions of the
    masses, labelled by the mass names of the model. The result is ``OK`` on every valid call (no warm-up). A frame with an infinite value, an empty frame, a frame without any joint (every row NaN) and a dict frame
    whose keys match none of the names the model reads are ``INVALID_INPUT`` (the cause is in ``result.reason``); a joint
    that is missing (absent from the dict, or a row with a NaN) is a dropout the model handles.

    **Time and units.** As in :class:`GenericModelSimulator`. The time step of a call is ``timestamp - previous timestamp`` in seconds, else ``1 / sampling_rate``, else 1 s. A
    timestamp that does not increase gives ``INVALID_INPUT`` (``"non-increasing timestamp"``) and leaves the model where it
    was; a non-finite timestamp raises ``ValueError``. The first timed call after construction or ``reset()`` uses
    ``1 / sampling_rate`` (or 1 s), never the absolute time.

    **Differences from EyesWeb.** ``prediction_interval`` is in seconds (EyesWeb: a time in 100 ns ticks); the propulsion
    factor of the original, which no force ever used, is not offered; ``length_forces``, ``rotation_forces``,
    ``ground_interaction`` and ``floor_position`` are parameters here.

    **Corrected in the core.** In ``"directions_linear"`` the z component of the extrapolated direction is its own z (the
    original used x), and the rest directions and lengths changed by the prediction are restored afterwards; the damping
    formulation is that of :class:`GenericModelSimulator`.

    Examples
    --------
    >>> from pyeyesweb.physical_signals import GenericModelPredictor, MassSpringModel
    >>> model = MassSpringModel()
    >>> model.add_mass("root", 1e10)
    >>> model.add_mass("tip", 1.0, (1.0, 0.0, 0.0))
    >>> model.add_spring("rod", "root", "tip", 1.0, 100.0, (1.0, 0.0, 0.0), 100.0)
    >>> predictor = GenericModelPredictor(model, sampling_rate=100.0, prediction_interval=0.2)
    >>> predictor.process([[0.0, 1.0, 0.0]]).positions[1].round(3)
    array([0.977, 0.231, 0.   ])
    """
    _core_class = _humanoid.GenericModelPredictor

    def __init__(self, model: Union[MassSpringModel, str, os.PathLike],
                 labels: Optional[Sequence[str]] = None, joint_map: Optional[Mapping[str, str]] = None,
                 **params: Any):
        _check_rate(params.get("sampling_rate"))
        super().__init__(model, labels, joint_map, **params)

    def process(self, directions: Any, *, timestamp: Optional[float] = None) -> Result:
        points = self._points(directions, timestamp)
        if isinstance(points, Result):
            return points
        step = self._time_step(timestamp)
        return self._result(positions=self._block.process_array(self._model_layout(), points, step), timestamp=timestamp)


@describe(Layer.PHYSICAL_SIGNALS, eyesweb="GenericModelEstimator")
class GenericModelEstimator(_Units, _Timed, _GenericFeature, CoreFeature):
    """Adaptive estimation of the parameters of a mass-spring model from observed joints.

    The model follows the observed positions of its masses and, while ``enable_adaptation`` is on, one parameter per frame
    is perturbed (a stochastic coordinate descent on a cost that weighs position, direction and speed errors); the change is
    kept when it lowers the cost. Over a recording the model therefore learns the masses and the spring stiffnesses and
    dampings that explain the observed movement, a way to identify the physical parameters of an articulated body.

    ``process(skeleton, *, timestamp=None)`` takes the observed positions of the masses of ``model`` (a dict
    ``label -> (x, y, z)`` or an ``(n_masses, 3)`` array in the order of ``labels``) and returns the simulated ``positions``
    and the ``error``. ``feature.model`` is a copy of the model with the parameters estimated so far
    (``feature.model.export_configuration()`` and ``feature.model.save_xml_file(path)``); ``feature.reset_step()`` sends the
    perturbation step back to ``initial_step`` and ``feature.current_step`` reads it.

    Parameters
    ----------
    model : MassSpringModel or str
        The initial model, or the path of an EyesWeb XML model file *(structural)*; replacing it restarts the state.
    labels : sequence of str, optional
        Names of the rows of array frames *(live)*. Default ``None``: the rows follow the order of ``model.mass_names``.
    joint_map : dict, optional
        ``mass name of the model -> label of your data`` *(live)*; names left out keep their own.
    reference_direction : tuple of float, default (1.0, 0.0, 0.0)
        Reference direction of the model *(live)*: the direction from which the rest directions of the springs are
        measured (dimensionless; the x axis by default).
    integration_step : float, default 0.001
        Step of the numerical integration in seconds, > 0 *(live)*. A call that advances the model by ``dt`` seconds runs
        ``int(dt / integration_step)`` steps.
    gravity : tuple of float, default (0.0, 0.0, 0.0)
        Gravity vector in ``units`` per second squared *(live)*; zero means no gravity.
    damping : float, default 10.0
        Damping coefficient of the springs *(live)*. The EyesWeb default, 0.3, makes chains of four or five bones diverge;
        10 is stable with noisy input and 3 follows clean data with less lag.
    viscosity : float, default 0.0
        Viscous friction of the masses *(live)*.
    length_forces : bool, default True
        Switch on the forces that keep each spring at its rest length *(live)*.
    rotation_forces : bool, default True
        Switch on the forces that turn each spring towards its target direction *(live)*.
    ground_interaction : bool, default False
        Add a floor, the plane through ``floor_position`` whose normal is opposite to gravity *(live)*; a mass below it is
        pushed back along the normal.
    floor_position : tuple of float, default (0.0, 0.0, 0.0)
        A point of the floor plane, in ``units`` *(live)*.
    use_input_lengths : bool, default False
        Take the rest length of each spring from the length of the input vector instead of the length of the model *(live)*.
    enable_adaptation : bool, default True
        Adapt the parameters *(live)*; off, the model only follows the input.
    estimate_masses : bool, default False
        Adapt the masses *(live)*.
    estimate_length_springs : bool, default False
        Adapt the length stiffness and the length damping of the springs *(live)*.
    estimate_direction_springs : bool, default False
        Adapt the direction stiffness and the direction damping of the springs *(live)*. With none of the three
        ``estimate_*`` switches on, nothing is adapted.
    step_is_absolute : bool, default False
        The perturbation is an absolute amount, in the unit of the parameter, instead of a fraction of the parameter
        *(live)*.
    initial_step : float, default 0.05
        Size of the perturbation at the start *(live)*; ``reset_step()`` returns to it.
    step_adaptation_factor : float, default 0.0001
        How fast the size of the perturbation adapts (dimensionless) *(live)*.
    cost_distance : float, default 1.0
        Weight of the position error in the cost (dimensionless) *(live)*.
    cost_directions : float, default 1.0
        Weight of the direction error in the cost *(live)*.
    cost_speed : float, default 1.0
        Weight of the speed error in the cost *(live)*.
    cost_length_stiffness : float, default 0.0
        Weight of the regulariser on the length stiffness *(live)*.
    cost_direction_stiffness : float, default 0.0
        Weight of the regulariser on the direction stiffness *(live)*.
    cost_length_damping : float, default 0.0
        Weight of the regulariser on the length damping *(live)*.
    cost_direction_damping : float, default 0.0
        Weight of the regulariser on the direction damping *(live)*.
    seed : int, default 12345
        Seed of the random draws, which makes a run reproducible (it replaces the unseeded ``rand()`` of EyesWeb)
        *(structural)*.
    sampling_rate : float, optional
        Frame rate in Hz, used for the time step of a call that has no ``timestamp`` *(live)*. Default ``None`` (no
        hidden rate): the step is then 1 s and ``reason`` says ``"no time given: per-sample derivatives"``.
    units : {"m", "mm"}, default "m"
        Name of the unit of the model, of the data, of ``gravity``, ``floor_position`` and of the outputs *(live)*; nothing
        is rescaled, as in :class:`GenericModelSimulator`.

    Notes
    -----
    **Outputs.** ``positions``: ``(n_masses, 3)`` array of ``(x, y, z)`` in ``units``, the simulated masses, labelled by
    the mass names of the model. ``error``: the cost of the frame, a weighted sum of the position, direction and speed
    errors (the weights are the ``cost_*`` parameters); it mixes quantities in the unit of the model, so its trend over a
    recording is more meaningful than its value. The result is ``OK`` on every valid call, and ``INVALID_INPUT`` with the
    reason ``"the result is not finite"`` when the simulation diverged. A frame with an infinite value, an empty frame, a frame without any joint (every row NaN) and a dict frame
    whose keys match none of the names the model reads are ``INVALID_INPUT`` (the cause is in ``result.reason``); a joint
    that is missing (absent from the dict, or a row with a NaN) is a dropout the model handles.

    **Time and units.** As in :class:`GenericModelSimulator`. The time step of a call is ``timestamp - previous timestamp`` in seconds, else ``1 / sampling_rate``, else 1 s. A
    timestamp that does not increase gives ``INVALID_INPUT`` (``"non-increasing timestamp"``) and leaves the model where it
    was; a non-finite timestamp raises ``ValueError``. The first timed call after construction or ``reset()`` uses
    ``1 / sampling_rate`` (or 1 s), never the absolute time.

    **Differences from EyesWeb.** ``seed``, ``length_forces``, ``rotation_forces``, ``ground_interaction`` and
    ``floor_position`` are parameters here; the model is saved on request instead of at every frame.

    **Corrected in the core.** The regularisers of the length and direction damping have their own weights (the original
    enabled them with the stiffness weights); the direction springs are adapted only when ``estimate_direction_springs``
    asks for it (the original always adapted them); the damping formulation is that of :class:`GenericModelSimulator`.

    Examples
    --------
    >>> from pyeyesweb.physical_signals import GenericModelEstimator, MassSpringModel
    >>> model = MassSpringModel()
    >>> model.add_mass("root", 1e10)
    >>> model.add_mass("tip", 1.0, (1.0, 0.0, 0.0))
    >>> model.add_spring("rod", "root", "tip", 1.0, 100.0, (1.0, 0.0, 0.0), 100.0)
    >>> estimator = GenericModelEstimator(model, sampling_rate=100.0, estimate_masses=True)
    >>> result = estimator.process([[0.0, 0.0, 0.0], [0.0, 1.0, 0.0]])    # the observed masses
    >>> result.positions.shape, bool(result.error > 0)
    ((2, 3), True)
    >>> sorted(estimator.model.export_configuration())[:2]               # the model as estimated so far
    ['mass::root::mass', 'mass::tip::mass']
    """
    _core_class = _humanoid.GenericModelEstimator
    _names_of = staticmethod(_mass_names)

    def __init__(self, model: Union[MassSpringModel, str, os.PathLike],
                 labels: Optional[Sequence[str]] = None, joint_map: Optional[Mapping[str, str]] = None,
                 **params: Any):
        _check_rate(params.get("sampling_rate"))
        super().__init__(model, labels, joint_map, **params)

    def _inputs(self) -> Inputs:
        return Inputs(self._frame_input("skeleton", "observed positions of the masses of the model"))

    def _schema(self) -> Schema:
        return Schema(self._positions_output(), Output("error", doc="cost of the frame"))

    def process(self, skeleton: Any, *, timestamp: Optional[float] = None) -> Result:
        points = self._points(skeleton, timestamp)
        if isinstance(points, Result):
            return points
        step = self._time_step(timestamp)
        positions, error = self._block.process_array(self._model_layout(), points, step)
        return self._finite_result(positions=positions, error=error, timestamp=timestamp)


# ---------------------------------------------------------------------------------------------------------------------
# points


@describe(Layer.PHYSICAL_SIGNALS, eyesweb="PointsPredictor")
class PointsPredictor(FrameFeature):
    r"""One-step linear extrapolation of labelled points.

    Each point is predicted one frame ahead by extending its last displacement,

    .. math::

        \hat{\mathbf{p}}(t) = \mathbf{p}(t) + \left(\mathbf{p}(t) - \mathbf{p}(t-1)\right),

    a constant-velocity forecast of where every tracked point will be at the next frame.

    ``process(points, *, timestamp=None)`` takes the points, a dict ``label -> (x, y, z)`` or an ``(N, 3)`` array in the
    order of ``labels``. The step is one frame: the feature has no time axis and ``timestamp`` is only copied into
    ``result.timestamp``. It is stateful (``reset()``).

    Parameters
    ----------
    labels : sequence of str, optional
        Names of the points, in the order of array frames; a dict frame is read by them. Fixed at construction. One of
        ``labels`` and ``skeleton`` is required, otherwise ``ValueError``.
    skeleton : str or Skeleton, optional
        A lab preset that gives the ``labels`` (``"kinect_v2"``, ``"qualisys_sport"``, ``"mediapipe"``, ``"openpose"``;
        see :mod:`pyeyesweb.skeletons`). Fixed at construction.

    Notes
    -----
    **Outputs.** ``predicted``: ``(N, 3)`` array of ``(x, y, z)`` in the unit of the data, labelled by ``labels``. A point
    seen for the first time (or after a gap) is returned unchanged. A point missing in a frame (absent from the dict, or a
    row with a NaN) is NaN in the output and forgotten. An infinite value, an empty frame and a frame without any point
    are ``INVALID_INPUT``; otherwise the result is ``OK`` (no warm-up).

    **Corrected in the core.** The original never stored the previous values and so never predicted anything; the output
    set is rebuilt at every call, so a label that disappears does not stay.

    Examples
    --------
    >>> from pyeyesweb.physical_signals import PointsPredictor
    >>> predictor = PointsPredictor(labels=["a", "b"])
    >>> predictor.process([[0.0, 0.0, 0.0], [1.0, 1.0, 1.0]]).predicted
    array([[0., 0., 0.],
           [1., 1., 1.]])
    >>> predictor.process([[1.0, 0.0, 0.0], [1.0, 2.0, 1.0]]).predicted
    array([[2., 0., 0.],
           [1., 3., 1.]])
    """
    _core_class = _humanoid.PointsPredictor

    def __init__(self, labels: Optional[Sequence[str]] = None, skeleton: Any = None):
        labels, _ = with_skeleton(skeleton, labels, {})
        if not labels:
            raise ValueError("PointsPredictor: no points given; pass labels= or skeleton=")
        if len(set(labels)) != len(labels):
            raise ValueError("PointsPredictor: repeated labels")
        super().__init__()
        self._labels = tuple(labels)
        self._layout = core.SkeletonLayout(list(labels))

    @property
    def labels(self) -> Tuple[str, ...]:
        """Names of the points."""
        return self._labels

    def _inputs(self) -> Inputs:
        return Inputs(points_input("points", self._labels, "labelled points", accepts=(dict,), allow_non_finite=True))

    def _schema(self) -> Schema:
        return Schema(Output("predicted", (len(self._labels), 3), labels=self._labels, components=XYZ,
                             unit="<length>", doc="linear extrapolation of each point one frame ahead"))

    def _process(self, frame: Any, timestamp: Optional[float]) -> Result:
        if isinstance(frame, dict):
            points = np.full((len(self._labels), 3), math.nan)
            for row, label in enumerate(self._labels):
                if label in frame:
                    points[row] = frame[label]
        else:
            points = np.asarray(frame, dtype=float)
            if points.size == 0:
                return self._no_output(Status.INVALID_INPUT, "empty frame", timestamp)
        if np.isinf(points).any():
            return self._no_output(Status.INVALID_INPUT, "infinite values", timestamp)
        if np.isnan(points).all():
            return self._no_output(Status.INVALID_INPUT, "no point present in the frame", timestamp)
        return self._result(predicted=self._block.process_array(self._layout, points), timestamp=timestamp)


__all__ = ["HumanoidSimulator", "HumanoidOrientations", "GenericModelOrientations", "GenericModelSimulator",
           "GenericModelPredictor", "GenericModelEstimator", "PointsPredictor", "MassSpringModel", "HUMANOID_JOINTS",
           "HUMANOID_BONES"]
