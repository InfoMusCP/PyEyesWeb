"""The humanoid's joint and bone tables and `MassSpringModel`, the model type of the features in `humanoid.py`."""

import os
from typing import Any, Tuple, Union

from pyeyesweb._core import core

_humanoid = core.humanoid

HUMANOID_JOINTS: Tuple[str, ...] = tuple(_humanoid.HumanoidSimulator().output_labels)
"""The 21 joints of the humanoid (EyesWeb Kinect SDK v1 names), in the order of the arrays it takes and returns."""

HUMANOID_BONES: Tuple[str, ...] = tuple(_humanoid.HumanoidOrientationsExtractor().output_labels)
"""The 20 bones of the humanoid, named `"<joint1>-<joint2>"`, in the order of `HumanoidOrientations`' output."""

# The joint names the block would otherwise take as parameters; `joint_map` replaces them.
NAME_PARAMS = frozenset({"spine_names", "left_arm_names", "right_arm_names", "left_leg_names", "right_leg_names"})

_CORE_MODEL = _humanoid.MassSpringModel


class MassSpringModel:
    """A named set of masses and springs (bones): the model of the `GenericModel*` features.

    Build it from an EyesWeb XML file (`MassSpringModel.from_xml_file(path)`; `<Model><Masses>...<Springs>...`) or
    by hand with `add_mass` and `add_spring`, and give it to a feature as `model=` (a path to an XML file is accepted
    there too). The features copy the model they get; `feature.model` returns a copy of its current state (the
    estimator's estimated parameters, for instance).

    Parameters
    ----------
    reference_direction : tuple of float, optional
        Reference direction of the rest directions of the springs (default the x axis).
    name : str, optional
        Name of the model.

    Methods
    -------
    from_xml_file(path), from_xml_string(xml)
        Load a model; the damping attributes of the file are relative (1 = critical damping).
    to_xml(), save_xml_file(path)
        The XML of the model (the damping written is the absolute coefficient, as the EyesWeb estimator does).
    add_mass(name, mass, position), add_spring(name, mass1, mass2, rest_length, length_stiffness, rest_direction,
    dir_stiffness, length_damping, dir_damping)
        Build the model by hand (`mass1` is the hinge of a spring, `mass2` its tip). Lengths and positions are in the
        unit of your data.
    export_configuration(), set_parameter(label, value)
        The parameters as a dict `label -> value` (`spring::<name>::stiffness`, `::damping`, `::dir_stiffness`,
        `::dir_damping`, `mass::<name>::mass`), and one parameter set by its label.
    mass_names, spring_names, spring_masses(name), positions()
        What the model holds.
    """

    def __init__(self, reference_direction: Tuple[float, float, float] = (1.0, 0.0, 0.0), name: str = "model"):
        self._model = _CORE_MODEL(reference_direction, name)

    @classmethod
    def _wrap(cls, model: Any) -> "MassSpringModel":
        wrapper = cls.__new__(cls)
        wrapper._model = model
        return wrapper

    @classmethod
    def from_xml_file(cls, path: Union[str, os.PathLike],
                      reference_direction: Tuple[float, float, float] = (1.0, 0.0, 0.0)) -> "MassSpringModel":
        """Load a model from an EyesWeb XML file. Raises `FileNotFoundError`, or `ValueError` for a malformed model."""
        if not os.path.isfile(path):
            raise FileNotFoundError(f"model file not found: {os.fspath(path)}")
        return cls._wrap(_loaded(_CORE_MODEL.from_xml_file, os.fspath(path), reference_direction))

    @classmethod
    def from_xml_string(cls, xml: str, reference_direction: Tuple[float, float, float] = (1.0, 0.0, 0.0)) -> "MassSpringModel":
        """Load a model from the text of an EyesWeb XML file."""
        return cls._wrap(_loaded(_CORE_MODEL.from_xml_string, xml, reference_direction))

    def save_xml_file(self, path: Union[str, os.PathLike]) -> None:
        """Write the model as an EyesWeb XML file."""
        self._model.save_xml_file(os.fspath(path))

    def __getattr__(self, name: str) -> Any:
        if name.startswith("_"):
            raise AttributeError(name)
        return getattr(self._model, name)

    def __repr__(self) -> str:
        return f"MassSpringModel({len(self._model.mass_names)} masses, {len(self._model.spring_names)} springs)"


def _loaded(load: Any, source: str, reference_direction: Tuple[float, float, float]) -> Any:
    """A model read by the core; a malformed one is a `ValueError`."""
    try:
        return load(source, reference_direction)
    except RuntimeError as error:
        raise ValueError(str(error)) from None


def core_model(model: Any) -> Any:
    """The core model of a `MassSpringModel`, of a core model, or loaded from the XML file `model` names."""
    if isinstance(model, MassSpringModel):
        return model._model
    if isinstance(model, _CORE_MODEL):
        return model
    if isinstance(model, (str, os.PathLike)):
        return MassSpringModel.from_xml_file(model)._model
    raise TypeError(f"model must be a MassSpringModel (MassSpringModel.from_xml_file(path), from_xml_string(xml), or built with "
                    f"add_mass / add_spring) or the path of an XML model file, got {type(model).__name__}")
