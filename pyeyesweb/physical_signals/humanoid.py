"""Mass-spring models of a body (EyesWeb HumanoidModel catalog): virtual sensors that turn a captured skeleton into a
physically simulated one, with its bone directions.

:class:`MassSpringSimulator` runs either a fixed 21-joint humanoid (``model="humanoid"``, the joints of the Kinect SDK v1
as EyesWeb names them; ``HUMANOID_JOINTS`` and ``HUMANOID_BONES`` list its joint and bone names) or a model of your own,
a :class:`MassSpringModel` (also loaded from an EyesWeb XML file), whose positions are in the unit of the model.

A frame is a dict ``label -> (x, y, z)`` or an ``(N, 3)`` array in the order of ``labels``. The model has its own joint
names; ``joint_map`` maps each of them to the label of your data (``{"head": "Head", ...}``; the names you do not list
keep their own name) and the constructor raises when the labels do not hold a joint the model needs. A joint that is
missing in a frame (absent from the dict, or a row with a NaN) is a dropout the model handles (its bones stay as they
were); infinite values and a frame without any joint are ``INVALID_INPUT``. Outputs are labelled by the names of the
model.

Time: the simulator advances the model by the time step of the call in seconds (the
library rule: ``timestamp``, else ``sampling_rate`` in Hz, default ``None``, else 1 s per call and the ``reason`` says
``"no time given: per-sample derivatives"``).

Units: ``units="m"|"mm"`` (default ``"m"``) is the unit of your frames, of ``gravity`` / ``floor_position`` and of the
outputs. The humanoid works internally in millimetres (the EyesWeb body is defined in mm) and converts at the
boundary, the one place where the library rescales data; a model of your own runs in the unit of their own model and
``units`` names it (stiffness and damping are in that unit).

Known limitation of the simulator: the rotation springs make chains of four or five bones flutter at a low ``damping``
and the model is not a noise filter; the default ``damping=10`` (EyesWeb: 0.3, which diverges) is stable, 3 follows
clean data with less lag.
"""

import math
import os
from typing import Any, ClassVar, Dict, Mapping, Optional, Sequence, Tuple, Union

import numpy as np

from pyeyesweb._core import core
from pyeyesweb.base.core_feature import XYZ, CoreFeature, VariantFeature
from pyeyesweb.base.inputs import points_input
from pyeyesweb.catalog import Layer, describe
from pyeyesweb.data_models.inputs import Input, InputKind, Inputs
from pyeyesweb.data_models.results import Output, Result, Schema, Status
from pyeyesweb.base.labels import LabelGuard
from pyeyesweb.physical_signals._humanoid_model import (
    HUMANOID_BONES, HUMANOID_JOINTS, NAME_PARAMS, MassSpringModel, core_model
)

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


# ---------------------------------------------------------------------------------------------------------------------
# the mass-spring simulator: the humanoid preset and a model of your own


_HUMANOID = "humanoid"
_ModelArgument = Union[str, MassSpringModel, os.PathLike]


@describe(Layer.PHYSICAL_SIGNALS, eyesweb="HumanoidSimulator (MassSpringHumanoidSimulator), GenericModelSimulator")
class MassSpringSimulator(VariantFeature, CoreFeature):
    r"""A physically based body of masses and springs that follows a captured skeleton.

    The captured joints are replaced by the pose of a virtual body: masses (the joints) joined by springs (the bones) are
    integrated in time. Every bone is a spring with a length force, which keeps its rest length, and a rotation force,
    which turns it towards the direction observed in the input. The simulated pose is smooth and always articulated, with
    the proportions of the model, so the feature acts as a virtual sensor that removes the jitter and the dropouts of a
    captured skeleton and yields a physically plausible joint trajectory. It is not a noise filter in the
    signal-processing sense (see Notes).

    ``model`` chooses the body:

    * ``"humanoid"`` (default): a fixed humanoid of 21 joints (``HUMANOID_JOINTS``, the joints of the first Kinect SDK as
      EyesWeb names them) and 20 bones (``HUMANOID_BONES``), hanging from its head (the EyesWeb HumanoidSimulator). Its
      bone directions are unit vectors relative to the parent bone.
    * a :class:`MassSpringModel`, or the path of an EyesWeb XML model file: a body of your own (a limb, a puppet, a rope;
      the EyesWeb GenericModelSimulator). The bone direction of a spring is the vector from its first mass (the hinge) to
      its second mass (the tip), :math:`\mathbf{b}_s = \mathbf{p}_{\mathrm{tip}(s)} - \mathbf{p}_{\mathrm{hinge}(s)}`,
      not normalised.

    ``process(joints, directions=None, *, timestamp=None)`` takes the captured joints, a dict ``label -> (x, y, z)`` or an
    ``(n_joints, 3)`` array in the order of ``labels`` (by default the order of ``inputs["joints"].labels``). The bone
    directions are read from the joints; the optional ``directions`` replaces them: an ``(n_bones, 3)`` array in the order
    of the ``directions`` output, or a dict ``bone -> (x, y, z)``, in the convention of that output (for the humanoid,
    unit directions relative to the parent bone; for a model of your own, world vectors). The ``directions`` output of a
    call, passed back, gives the pose of the joints it came from.

    Parameters
    ----------
    labels : sequence of str, optional
        Names of the rows of array frames *(live)*. Default ``None``: the rows follow the joint names of the model
        (``HUMANOID_JOINTS``, or the mass names of your model).
    joint_map : dict, optional
        ``joint of the model -> label of your data`` *(live)*; the names you leave out keep their own. The constructor
        raises ``ValueError`` when ``labels`` lack a joint the model needs.
    model : {"humanoid"} or MassSpringModel or str
        The body. ``"humanoid"`` (default) is the 21-joint humanoid, fixed for the life of the feature; a
        :class:`MassSpringModel` or the path of an EyesWeb XML file is a model of your own *(structural)*, which can be
        replaced by another model of your own.
    start_from_input : bool, default False
        Put the model on the first frame after construction or ``reset()`` instead of letting it settle there from its
        rest pose *(live)*. The joints that are present take the input positions and that first frame is returned as it
        is; for the humanoid the rest lengths of the bones become the bone lengths of the input. A change applies from
        the next ``reset()``.
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
    use_input_lengths : bool, default False
        Take the rest length of each spring from the length of its input bone vector instead of the length of the model
        *(live)*. A model of your own only.

    Notes
    -----
    **Outputs.** ``joints``: ``(n_joints, 3)`` array of ``(x, y, z)`` in ``units``, the simulated positions, labelled by
    the joint names of the model; a joint the model did not produce is NaN. ``directions``: ``(n_bones, 3)``, the bone
    directions the model followed in this call (the ones read from the joints, or the ``directions`` given), labelled by
    the bone names (``HUMANOID_BONES``, or the spring names of your model in alphabetical order). For the humanoid they are
    unit vectors relative to the parent bone, dimensionless (a bone of zero length gives the zero vector, and a joint
    missing in a frame keeps the position it had in the previous frame, the T-pose before the first); for a model of your
    own they are world vectors in ``units`` (NaN for a spring with a missing mass). The result is ``OK`` on every valid
    call (there is no warm-up). A frame with an infinite value, an empty frame, a frame without any joint (every row NaN)
    and a dict frame whose keys match none of the names the model reads are ``INVALID_INPUT`` (the cause is in
    ``result.reason``); a joint that is missing (absent from the dict, or a row with a NaN) is a dropout the model handles:
    its bones keep their target.

    **Time.** The time step of a call is ``timestamp - previous timestamp`` in seconds, else ``1 / sampling_rate``, else
    1 s. A timestamp that does not increase gives ``INVALID_INPUT`` (``"non-increasing timestamp"``) and leaves the model
    where it was; a non-finite timestamp raises ``ValueError``. The first timed call after construction or ``reset()``
    uses ``1 / sampling_rate`` (or 1 s), never the absolute time.

    **Units.** The EyesWeb humanoid is defined in millimetres and the spring forces depend on the length unit, so the
    humanoid works internally in millimetres and converts at the boundary: with ``units="m"`` frames are multiplied by
    1000 on the way in and joints divided by 1000 on the way out. A body driven in metres reproduces the millimetre run up
    to rounding. A model of your own runs in its own unit, and ``units`` only names it: nothing is rescaled, and its
    stiffness and damping are expressed in that unit (an EyesWeb XML model is usually in millimetres: ``units="mm"``).

    **Behaviour.** The humanoid hangs from its head: the output is the pose of a body hanging from where its head starts,
    the T-pose at the origin or, with ``start_from_input``, the first frame; the translation of the person is not
    followed, as in EyesWeb. Bone lengths stay those of the model and only the directions follow the input. ``reset()``
    puts the body back in its rest pose.

    **Known limitation.** The rotation springs make chains of four or five bones flutter at a low ``damping``, and the
    model is not a noise filter: it follows the input with a lag that grows with ``damping``.

    **Differences from EyesWeb.** One feature for the two EyesWeb simulators and their orientation extractors (the bone
    directions are an output); the default ``damping`` is 10 (EyesWeb: 0.3, which diverges); time is in seconds per call;
    the humanoid reads ``directions`` relative to the parent bone (EyesWeb read world directions, so there the output of
    its orientation extractor gave another pose).

    **Corrected in the core.** The damping force is proportional to the relative velocity of the two masses (the original
    used speed magnitudes and injected energy); the feet of the T-pose are built along the direction they rest in, so the
    body at rest is in equilibrium; the reset to the input, which the original humanoid could never reach, works and moves
    only the joints that are present; after the reset of a model of your own the spring directions are refreshed; the zero
    vector normalises to the zero vector instead of NaN.

    Examples
    --------
    >>> import numpy as np
    >>> from pyeyesweb.physical_signals import MassSpringModel, MassSpringSimulator
    >>> simulator = MassSpringSimulator(sampling_rate=25.0)
    >>> result = simulator.process({"head": (0.0, 1.7, 0.0)})    # a lone joint: the body hangs from it, in its T-pose
    >>> result.joints.shape, result.directions.shape
    ((21, 3), (20, 3))
    >>> follower = MassSpringSimulator(sampling_rate=25.0, start_from_input=True)
    >>> bool(np.allclose(follower.process(result.joints).joints, result.joints))
    True

    A model of your own: a rod of length 1 hanging from a heavy root, asked to point along y.

    >>> model = MassSpringModel()
    >>> model.add_mass("root", 1e10)
    >>> model.add_mass("tip", 1.0, (1.0, 0.0, 0.0))
    >>> model.add_spring("rod", "root", "tip", 1.0, 100.0, (1.0, 0.0, 0.0), 100.0)
    >>> rod = MassSpringSimulator(model=model, sampling_rate=100.0)
    >>> rod.inputs["joints"].labels
    ('root', 'tip')
    >>> for _ in range(3):
    ...     result = rod.process([[0.0, 0.0, 0.0], [0.0, 1.0, 0.0]])
    >>> result.directions
    array([[0., 1., 0.]])
    """
    _SWITCH = ("model", _HUMANOID)
    _switch_annotation = _ModelArgument
    _variants: ClassVar[dict] = {}
    _timed = True  # both bodies advance by the time step of each call (the catalog-wide time tests read it here)

    @classmethod
    def _variant_key(cls, value: Any) -> str:
        return _HUMANOID if isinstance(value, str) and value.strip().lower() == _HUMANOID else "custom"

    def _inputs(self) -> Inputs:
        bones = self._bone_names()
        return Inputs(self._frame_input("joints", "captured joints, in `units`"),
                      Input("directions", InputKind.POINTS, (len(bones), 3), bones, doc=(
                          "bone directions replacing those read from the joints, in the convention of the `directions` "
                          "output"), accepts=(dict,), optional=True, allow_non_finite=True))

    def _schema(self) -> Schema:
        joints, bones = self._joint_names(), self._bone_names()
        return Schema(Output("joints", (len(joints), 3), labels=joints, components=XYZ, unit=self._units_output(),
                             doc="simulated joint positions"),
                      Output("directions", (len(bones), 3), labels=bones, components=XYZ,
                             unit=self._directions_unit(), doc="bone directions followed by the model"))

    def _directions_array(self, directions: Any) -> np.ndarray:
        """`directions` given by the user as the `(n_bones, 3)` array of the `directions` output (NaN: no direction)."""
        bones = self._bone_names()
        if isinstance(directions, dict):
            out = np.full((len(bones), 3), math.nan)
            for row, name in enumerate(bones):
                if name in directions:
                    out[row] = directions[name]
            return out
        return np.asarray(directions, dtype=float)

    def process(self, joints: Any, directions: Any = None, *, timestamp: Optional[float] = None) -> Result:
        points = self._points(joints, timestamp)
        if isinstance(points, Result):
            return points
        step = self._time_step(timestamp)
        given = None if directions is None else self._directions_array(directions)
        positions, followed = self._simulate(points, given, step, self._teleport())
        return self._result(joints=positions, directions=followed, timestamp=timestamp)


class _Humanoid(_Units, _Simulator, _ModelInput, MassSpringSimulator, variant=_HUMANOID):
    """The ``model="humanoid"`` body of ``MassSpringSimulator``; see that class for the parameters and the outputs."""

    _core_class = _humanoid.HumanoidSimulator
    _hidden_params = NAME_PARAMS
    _internal_mm = True

    def __init__(self, labels: Optional[Sequence[str]] = None, joint_map: Optional[Mapping[str, str]] = None,
                 *, model: _ModelArgument = _HUMANOID, start_from_input: bool = False, **params: Any):
        _check_rate(params.get("sampling_rate"))
        self._start_from_input = _switch("start_from_input", start_from_input)
        super().__init__(**params)
        self._set_input(labels, joint_map)
        self._layout = core.SkeletonLayout(list(HUMANOID_JOINTS))

    @property
    def model(self) -> str:
        """``"humanoid"``: the body of this feature, fixed for its life."""
        return _HUMANOID

    @model.setter
    def model(self, value: Any) -> None:
        raise AttributeError("MassSpringSimulator: the humanoid body is fixed; build a new MassSpringSimulator(model=...) "
                             "for a model of your own")

    def _input_names(self) -> Tuple[str, ...]:
        return HUMANOID_JOINTS

    def _joint_names(self) -> Tuple[str, ...]:
        return HUMANOID_JOINTS

    def _bone_names(self) -> Tuple[str, ...]:
        return HUMANOID_BONES

    def _directions_unit(self) -> Optional[str]:
        return None  # unit vectors

    @property
    def _extractor(self) -> Any:
        """The orientation extractor of the humanoid, for the `directions` output. It holds the last position of every
        joint, so it lives as long as the simulator and is rebuilt only when the reference direction changes."""
        extractor = self.__dict__.get("_extractor_block")
        if extractor is None:
            reference = self._block_params(self._params).get("ref_dir")
            extractor = _humanoid.HumanoidOrientationsExtractor() if reference is None else \
                _humanoid.HumanoidOrientationsExtractor(ref_dir=reference)
            self.__dict__["_extractor_block"] = extractor
        return extractor

    def _set_param(self, name: str, value: Any) -> None:
        super()._set_param(name, value)
        if name == "reference_direction":
            self.__dict__.pop("_extractor_block", None)

    def reset(self) -> None:
        super().reset()
        self._extractor.reset()

    def _simulate(self, points: np.ndarray, given: Optional[np.ndarray], step: float,
                  teleport: bool) -> Tuple[np.ndarray, np.ndarray]:
        scale = self._to_core
        if scale != 1.0:  # metres in, the core works in mm
            points = points * scale
        observed = self._extractor.process_array(self._layout, points)
        if given is None:
            raw = self._block.process_array(self._layout, points, step, teleport)
        else:
            joints = {name: tuple(row) for name, row in zip(HUMANOID_JOINTS, points.tolist()) if not np.isnan(row).any()}
            control = {name: tuple(row) for name, row in zip(HUMANOID_BONES, given.tolist()) if np.isfinite(row).all()}
            out = self._block.process(joints, step, control, teleport)
            raw = np.array([out.get(name, _NAN_POINT) for name in self._block.output_labels])
        if scale != 1.0:
            raw = raw / scale
        return raw, observed if given is None else given


class _Custom(_Units, _Simulator, _ModelInput, MassSpringSimulator, variant="custom"):
    """A ``MassSpringModel`` body of ``MassSpringSimulator``; see that class for the parameters and the outputs."""

    _core_class = _humanoid.GenericModelSimulator

    def __init__(self, labels: Optional[Sequence[str]] = None, joint_map: Optional[Mapping[str, str]] = None,
                 *, model: _ModelArgument, start_from_input: bool = False, **params: Any):
        _check_rate(params.get("sampling_rate"))
        self._start_from_input = _switch("start_from_input", start_from_input)
        super().__init__(model=model, **params)
        self._set_input(labels, joint_map)

    @classmethod
    def _coerce_choices(cls, params: dict) -> dict:
        out = super()._coerce_choices(params)
        if "model" in out:
            if isinstance(out["model"], str) and out["model"].strip().lower() == _HUMANOID:
                raise ValueError("MassSpringSimulator: model='humanoid' is another kind of body; build a new "
                                 "MassSpringSimulator for it")
            out["model"] = core_model(out["model"])
        return out

    @property
    def model(self) -> MassSpringModel:
        """A copy of the model in its current state. Setting it changes the model; the state restarts and the labels
        are checked against the new mass names."""
        return MassSpringModel._wrap(self._block.model)

    @model.setter
    def model(self, value: Any) -> None:
        model = self._coerce_choices({"model": value})["model"]
        self._set_input(self._labels, self._given_map, tuple(model.mass_names))  # checks before anything changes
        try:
            self._set_param("model", model)
        except Exception:
            self._set_input(self._labels, self._given_map)
            raise

    def _input_names(self) -> Tuple[str, ...]:
        return tuple(self._params["model"].mass_names)

    def _joint_names(self) -> Tuple[str, ...]:
        return tuple(self._block.output_labels)

    def _bone_names(self) -> Tuple[str, ...]:
        return tuple(self._extractor.output_labels)

    def _directions_unit(self) -> Optional[str]:
        return self._units_output()

    def _outputs_changed(self) -> None:
        for cached in ("_extractor_block", "_mass_layout", "_bone_layout"):
            self.__dict__.pop(cached, None)
        super()._outputs_changed()

    def _cached(self, key: str, build: Any) -> Any:
        value = self.__dict__.get(key)
        if value is None:
            value = self.__dict__[key] = build()
        return value

    @property
    def _extractor(self) -> Any:
        """The bone vectors of the model (stateless): rebuilt when the model changes."""
        return self._cached("_extractor_block", lambda: _humanoid.GenericModelOrientationsExtractor(self._params["model"]))

    def _simulate(self, points: np.ndarray, given: Optional[np.ndarray], step: float,
                  teleport: bool) -> Tuple[np.ndarray, np.ndarray]:
        masses = self._cached("_mass_layout", lambda: core.SkeletonLayout(list(self._input_names())))
        bones = self._cached("_bone_layout", lambda: core.SkeletonLayout(list(self._bone_names())))
        followed = self._extractor.process_array(masses, points) if given is None else given
        return self._block.process_array(bones, np.ascontiguousarray(followed), step, reset_to_input=teleport), followed


for _variant in (_Humanoid, _Custom):
    _variant.__name__ = MassSpringSimulator.__name__


__all__ = ["MassSpringSimulator", "MassSpringModel", "HUMANOID_JOINTS", "HUMANOID_BONES"]
