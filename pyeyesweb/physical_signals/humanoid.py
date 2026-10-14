"""Mass-spring models of a body (EyesWeb HumanoidModel catalog): virtual sensors that turn a captured skeleton into a
physically simulated one, into bone directions or into a prediction.

* `HumanoidSimulator`, `HumanoidOrientations`: a fixed 21-joint humanoid (the Kinect SDK v1 joints of EyesWeb, built in
  millimetres and simulated in millimetres); `HUMANOID_JOINTS` and `HUMANOID_BONES` list its joint and bone names.
* `GenericModelOrientations`, `GenericModelSimulator`, `GenericModelPredictor`, `GenericModelEstimator`: the same
  blocks for a model of your own, a [MassSpringModel][pyeyesweb.physical_signals.humanoid.MassSpringModel] (also loaded
  from an EyesWeb XML file). Positions are in the unit of the model.
* `PointsPredictor`: one-step linear extrapolation of any labelled points.

A frame is a dict `label -> (x, y, z)` or an `(N, 3)` array in the order of `labels`. The model has its own joint names;
`joint_map` maps each of them to the label of your data (`{"head": "Head", ...}`; the names you do not list keep their own
name) and the constructor raises when the labels do not hold a joint the model needs. A joint that is missing in a frame
(absent from the dict, or a row with a NaN) is a dropout the block handles (its bones stay as they were); infinite values
and a frame without any joint are `INVALID_INPUT`. Outputs are labelled by the names of the model.

Time: the simulators, the predictor and the estimator advance the model by the time step of the call in seconds (the
library rule: `timestamp`, else `sampling_rate` in Hz, default None, else 1 s per call and the `reason` says
"no time given: per-sample derivatives").

Units: `units="m"|"mm"` (default "m") is the unit of your frames, of `gravity` / `floor_position` and of the outputs.
`HumanoidSimulator` works internally in millimetres (the EyesWeb body is defined in mm) and converts at the boundary,
the one place where the library rescales data; the generic models run in the unit of their own model and `units` names
it (stiffness and damping are in that unit).

KNOWN LIMITATION of the simulators: the rotation springs make chains of 4-5 bones flutter at a low `damping` and the
model is not a noise filter (see `EyesWebCore/PORTING_STATUS.md`, "Deviations from EyesWeb (humanoid)"): the default
`damping=10` (EyesWeb: 0.3, which diverges) is stable, 3 follows clean data with less lag.
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
    """A physically based humanoid that follows a captured skeleton (EyesWeb HumanoidSimulator).

    The body has the 21 joints of `HUMANOID_JOINTS`. EyesWeb defines it in millimetres and this feature works
    internally in millimetres: `units` declares the unit of YOUR frames and outputs (`"m"` by default, or `"mm"`) and the
    feature converts at the boundary (frames times 1000 for metres on the way in, joints divided by 1000 on the way out;
    nothing for `"mm"`, which is bit for bit the core). This is the one place where the library rescales data, because
    the spring forces depend on the length unit: the same body gives the same motion whatever your unit. The stiffness
    and the damping are those of the model in mm, kg and s. Metres equal the millimetre run only up to rounding (the
    conversion is a multiplication, and the model is sensitive to tiny differences over long noisy runs). Every
    bone is a spring with a length force and a rotation force towards the direction observed in the input; the head is
    the (heavy) root. The simulated pose is smooth and always articulated, it is not a noise filter (see the module
    documentation for the flutter at a low `damping`).

    `process(skeleton, control=None, *, timestamp=None)` takes the captured joints and returns `joints`, the
    simulated positions `(21, 3)` in mm labelled by `HUMANOID_JOINTS`. `control` (optional) holds bone directions, an
    `(20, 3)` array in the order of `HUMANOID_BONES` or a dict `"<joint1>-<joint2>" -> (x, y, z)`; the bones follow them
    instead of the directions seen in the joints. They are directions RELATIVE to the parent bone, the convention of the
    output of `HumanoidOrientations`: piping the extractor's output into `control` reproduces the pose of the joints it
    came from. (EyesWeb read them as world directions, so there its extractor's output gave another pose.)

    Parameters
    ----------
    labels : sequence of str, optional
        Names of the rows of array frames. Default: the rows are in the order of `HUMANOID_JOINTS`.
    joint_map : dict, optional
        `joint of the model -> label of your data` (the model names are those of `HUMANOID_JOINTS`; those you leave out
        keep their own name). Raises at construction when `labels` lack a joint the model needs.
    sampling_rate : float, optional
        Frame rate in Hz when no `timestamp` is given (default None). Time is in seconds: the `timestamp`, else
        `sampling_rate`, else 1 s per call and the `reason` says "no time given: per-sample derivatives".
    units : {"m", "mm"}
        Unit of the frames, of the outputs and of `gravity` and `floor_position` (default "m"; Qualisys: "mm").
    start_from_input : bool, optional
        Put the model on the first frame after construction or `reset()` instead of letting it settle from the T-pose
        (default False).
    reference_direction : tuple of float
        Reference direction of the body (default the x axis).
    integration_step : float
        Integration step in seconds (default 0.001); a call of dt seconds runs `int(dt / integration_step)` steps.
    gravity : tuple of float
        Gravity in `units` / s^2 (default none).
    damping : float
        Damping coefficient (default 10; EyesWeb 0.3 diverges on long chains).
    viscosity : float
        Viscous friction (default 0).
    length_forces, rotation_forces : bool
        Switch the length and the rotation springs on or off.
    ground_interaction : bool
        A floor plane through `floor_position` with its normal against gravity.
    floor_position : tuple of float
        A point of the floor plane, in `units`.

    Returns
    -------
    joints : `(21, 3)` array, in `units`
        Simulated joint positions; a joint the block did not produce is NaN.

    Notes
    -----
    The head is pinned (a mass of 1e10): the output is the pose of a body hanging from where its head starts, the T-pose
    at the origin or the first frame with `start_from_input`, which also gives the body the proportions of the
    captured person; the translation of the person is not followed (as in EyesWeb). Bone lengths stay those of the
    body, only the directions follow the input. A joint missing in a frame leaves its bones unchanged. All parameters
    are live. `process` is stateful: `reset()` puts the body back in the T-pose.
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
    """The orientation of every bone of a skeleton relative to its parent bone (EyesWeb HumanoidOrientationsExtractor).

    `process(skeleton, *, timestamp=None)` returns `directions`, the unit direction of each of the 20 bones of
    `HUMANOID_BONES` (labelled `"<joint1>-<joint2>"`), expressed in the frame of the previous bone: a pose description
    that does not depend on the orientation of the parent (the convention of the `control` input of
    `HumanoidSimulator`, which takes this output as it is). A zero-length
    bone gives the zero vector. A joint missing in a frame keeps the position it had in the previous one (the T-pose
    before the first), so a bone with a joint that never was seen is still computed. Stateful (`reset()`); no time.

    Parameters
    ----------
    labels : sequence of str, optional
        Names of the rows of array frames. Default: the rows are in the order of `HUMANOID_JOINTS`.
    joint_map : dict, optional
        `joint of the model -> label of your data`, see `HumanoidSimulator`.
    reference_direction : tuple of float
        Reference direction of the root bones (default the x axis).

    Returns
    -------
    directions : `(20, 3)` array
        Unit bone directions, dimensionless.
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
    """The bone vectors of a mass-spring model from the positions of its masses (EyesWeb GenericModelOrientationsExtractor).

    `process(skeleton, *, timestamp=None)` takes the positions of the masses (one point per mass of `model`, named
    like the mass, or mapped with `joint_map`) and returns `directions`: for every spring, the vector from its first to
    its second mass (`mass2 - mass1`, not normalised, in the unit of the data), labelled by the spring name. A spring
    with a missing mass is NaN. It is the input of `GenericModelSimulator` and `GenericModelPredictor`. Stateless.

    Parameters
    ----------
    model : MassSpringModel or str
        The model, or the path of an EyesWeb XML model file.
    labels : sequence of str, optional
        Names of the rows of array frames. Default: the rows are in the order of `model.mass_names`.
    joint_map : dict, optional
        `mass name of the model -> label of your data` (names left out keep their own).

    Returns
    -------
    directions : `(n_springs, 3)` array
        Bone vectors, in the unit of the data.

    Examples
    --------
    >>> model = MassSpringModel.from_xml_file("model.xml")
    >>> GenericModelOrientations(model).run(masses)["directions"]  # `masses`: (frames, n_masses, 3)
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
    """A mass-spring model that follows bone directions (EyesWeb GenericModelSimulator).

    `process(directions, *, timestamp=None)` takes one direction per spring of `model` (labelled by the spring name,
    or mapped with `joint_map`; the output of `GenericModelOrientations`) as the rest targets of the springs, advances
    the model by the time step and returns `positions`, the masses of the model in `units`. A direction
    missing in a frame leaves its spring unchanged. All parameters are live except `model` (structural).
    See `HumanoidSimulator` for the flutter at a low `damping`.

    Units: the model, the data, `gravity`, `floor_position` and the outputs are all in the same unit, the one you
    declare with `units` (default "m"; an EyesWeb XML model is usually in mm: `units="mm"`). Nothing is rescaled: the
    dynamics are those of the model in its own length unit, and the stiffness and damping are in that unit too (the same
    model declared in another unit moves differently). `units` only names the unit of the outputs.

    Parameters
    ----------
    model : MassSpringModel or str
        The model, or the path of an EyesWeb XML model file.
    labels : sequence of str, optional
        Names of the rows of array frames. Default: the rows are in the order of `model.spring_names`.
    joint_map : dict, optional
        `spring name of the model -> label of your data` (names left out keep their own).
    sampling_rate : float, optional
        Frame rate in Hz when no `timestamp` is given (default None). Time is in seconds: the `timestamp`, else
        `sampling_rate`, else 1 s per call and the `reason` says "no time given: per-sample derivatives".
    units : {"m", "mm"}
        Unit of the model, the data, `gravity`, `floor_position` and the outputs (default "m").
    start_from_input : bool, optional
        Move the tips of the springs onto the input at the first frame after construction or `reset()` (default False).
    reference_direction : tuple of float
        Reference direction of the model (default the x axis).
    integration_step : float
        Integration step in seconds (default 0.001).
    gravity : tuple of float
        Gravity, in `units` per s^2.
    damping : float
        Damping coefficient (default 10; EyesWeb 0.3 diverges on long chains).
    viscosity : float
        Viscous friction (default 0).
    length_forces, rotation_forces : bool
        Switch the length and the rotation springs on or off.
    ground_interaction : bool
        A floor plane through `floor_position`.
    floor_position : tuple of float
        A point of the floor plane, in `units`.
    use_input_lengths : bool
        Take the rest length of each spring from the input vector (default False: the length of the model).

    Returns
    -------
    positions : `(n_masses, 3)` array
        Positions of the masses, in `units`.

    Examples
    --------
    >>> model = MassSpringModel.from_xml_file("model.xml")
    >>> simulator = GenericModelSimulator(model, units="mm", sampling_rate=100)
    >>> simulator.process(directions).positions  # `directions`: the output of GenericModelOrientations
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
    """The positions a mass-spring model will have a short time ahead (EyesWeb GenericModelPredictor).

    Like `GenericModelSimulator` it follows the bone directions of each frame; `positions` is where the masses are
    `prediction_interval` seconds later, with the model left to move on its own (`mode="masses_inertia"`: the masses
    keep their velocity; `"directions_linear"`: the bone directions are extrapolated linearly). The state of the model
    is the one of the follower: the prediction does not disturb it.

    Parameters
    ----------
    model : MassSpringModel or str
        The model, or the path of an EyesWeb XML model file.
    labels : sequence of str, optional
        Names of the rows of array frames. Default: the rows are in the order of `model.spring_names`.
    joint_map : dict, optional
        `spring name of the model -> label of your data` (names left out keep their own).
    sampling_rate : float, optional
        Frame rate in Hz when no `timestamp` is given (default None); time rule and `units` as in
        `GenericModelSimulator`.
    units : {"m", "mm"}
        Unit of the model, the data, `gravity`, `floor_position` and the outputs (default "m").
    prediction_interval : float
        How far ahead to predict, in seconds (default 0.2).
    mode : {"masses_inertia", "directions_linear"}
        How the future is computed (default `"masses_inertia"`).
    damping_factor, viscosity_factor : float
        Factors of `damping` and `viscosity` while predicting (default 1).
    reference_direction, integration_step, gravity, damping, viscosity, length_forces, rotation_forces, ground_interaction, floor_position, use_input_lengths
        As in `GenericModelSimulator`.

    Returns
    -------
    positions : `(n_masses, 3)` array
        Predicted positions of the masses, in `units`.

    Examples
    --------
    >>> model = MassSpringModel.from_xml_file("model.xml")
    >>> predictor = GenericModelPredictor(model, units="mm", sampling_rate=100, prediction_interval=0.1)
    >>> predictor.process(directions).positions  # `directions`: the output of GenericModelOrientations
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
    """Adaptive estimation of the parameters of a mass-spring model from observed joints (EyesWeb GenericModelEstimator).

    `process(skeleton, *, timestamp=None)` takes the observed positions of the masses of `model`, follows them with the
    model and, when `enable_adaptation` is on, perturbs one parameter per frame (a stochastic coordinate descent on a
    cost of direction, position and speed errors) and keeps the change that lowers the cost. It returns the simulated
    `positions` and the `error`, the cost of the frame. `feature.model` is the model with the estimated parameters
    (`feature.model.export_configuration()`, `save_xml_file`); `feature.reset_step()` sends the step back to
    `initial_step` and `feature.current_step` reads it. The draws are reproducible: `seed` replaces the `rand()` of
    EyesWeb.

    Parameters
    ----------
    model : MassSpringModel or str
        The initial model, or the path of an EyesWeb XML model file.
    labels : sequence of str, optional
        Names of the rows of array frames. Default: the rows are in the order of `model.mass_names`.
    joint_map : dict, optional
        `mass name of the model -> label of your data` (names left out keep their own).
    sampling_rate : float, optional
        Frame rate in Hz when no `timestamp` is given (default None); time rule and `units` as in
        `GenericModelSimulator`.
    units : {"m", "mm"}
        Unit of the model, the data, `gravity`, `floor_position` and the outputs (default "m").
    enable_adaptation : bool
        Adapt the parameters (default True).
    estimate_masses, estimate_length_springs, estimate_direction_springs : bool
        Which parameters are adapted (default none; with none selected nothing changes).
    step_is_absolute : bool
        The perturbation is an absolute amount instead of a fraction of the parameter (default False).
    initial_step, step_adaptation_factor : float
        Size of the perturbation and how fast it adapts (defaults 0.05 and 0.0001).
    cost_distance, cost_directions, cost_speed : float
        Weights of the position, direction and speed errors in the cost (default 1).
    cost_length_stiffness, cost_direction_stiffness, cost_length_damping, cost_direction_damping : float
        Regularisation weights of the parameters (default 0).
    seed : int
        Seed of the random draws (default 12345).
    reference_direction, integration_step, gravity, damping, viscosity, length_forces, rotation_forces, ground_interaction, floor_position, use_input_lengths
        As in `GenericModelSimulator`.

    Returns
    -------
    positions : `(n_masses, 3)` array
        Simulated positions of the masses, in `units`.
    error : float
        Cost of the frame.

    Examples
    --------
    >>> model = MassSpringModel.from_xml_file("model.xml")
    >>> estimator = GenericModelEstimator(model, units="mm", sampling_rate=100, estimate_masses=True)
    >>> result = estimator.process(masses)      # `masses`: one frame of mass positions
    >>> result.error, estimator.model            # the cost of the frame, the model as estimated so far
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
    """One-step linear extrapolation of labelled points (EyesWeb PointsPredictor).

    `process(points, *, timestamp=None)` returns `predicted`, `p(t) + (p(t) - p(t-1))` for each point; a point seen
    for the first time (or after a gap) is returned unchanged. A point missing in a frame (absent from a dict, or a row
    with a NaN) is NaN in the output and forgotten. Stateful (`reset()`); the step is one frame, no time.

    Parameters
    ----------
    labels : sequence of str, optional
        Names of the points, in the order of array frames; a dict frame is read by them.
    skeleton : str or Skeleton, optional
        A lab preset giving the `labels` (see `pyeyesweb.skeletons`). One of `labels` and `skeleton` is required.

    Returns
    -------
    predicted : `(N, 3)` array
        Predicted positions, in the unit of the data.
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
