"""Choice parameters are strings (case-insensitive), as in scikit-learn; ON/OFF parameters are plain bools.
Needs the compiled core (EYESWEB_CORE_PATH)."""
import os
import sys
from functools import partial

import pytest

if os.environ.get("EYESWEB_CORE_PATH"):
    sys.path.insert(0, os.environ["EYESWEB_CORE_PATH"])
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

pytest.importorskip("pyeyesweb._core", exc_type=ImportError)

from pyeyesweb._core import core  # noqa: E402
from pyeyesweb.analysis_primitives import Rarity  # noqa: E402
from pyeyesweb.analysis_primitives.synchronization import EventSynchronization  # noqa: E402
from pyeyesweb.low_level import Kinematics, KineticEnergy, Symmetry  # noqa: E402

# (feature class, parameter, string) for one core enum of each area.
CASES = [
    (partial(KineticEnergy, weights={"head": 1.0}), "input_mode", "velocity"),
    (Kinematics, "output_type", "acceleration"),
]


@pytest.mark.parametrize("cls, name, text", CASES)
def test_a_string_is_the_parameter_and_reads_back_as_a_string(cls, name, text):
    assert getattr(cls(**{name: text}), name) == text


@pytest.mark.parametrize("cls, name, text", CASES)
@pytest.mark.parametrize("spelling", ["upper", "title", "dash", "space"])
def test_case_dash_and_space_are_tolerated(cls, name, text, spelling):
    written = {"upper": text.upper(), "title": text.title(), "dash": text.replace("_", "-"),
               "space": f" {text.replace('_', ' ')} "}[spelling]
    assert getattr(cls(**{name: written}), name) == text


@pytest.mark.parametrize("cls, name, text", CASES)
def test_invalid_string_names_the_parameter_and_lists_the_options(cls, name, text):
    with pytest.raises(ValueError, match=name) as error:
        cls(**{name: "nonsense"})
    assert repr(text) in str(error.value)


def test_an_enum_member_still_works():
    assert KineticEnergy(weights={"head": 1.0}, input_mode=core.motion.KineticEnergyInputMode.VELOCITY).input_mode == "velocity"


def test_runtime_assignment_by_string():
    energy = KineticEnergy(weights={"head": 1.0})
    energy._block  # a built block takes the new value over
    energy.input_mode = "velocity"
    assert energy.input_mode == "velocity" and energy._block_params(energy._params)["input_mode"] is core.motion.KineticEnergyInputMode.VELOCITY
    with pytest.raises(ValueError, match="input_mode"):
        energy.input_mode = "nonsense"
    assert energy.input_mode == "velocity"


def test_none_and_other_parameters_are_untouched():
    assert KineticEnergy._coerce_choices({"input_mode": None, "sampling_rate": 25}) == {"input_mode": None,
                                                                                      "sampling_rate": 25}


def test_bool_parameter_is_live_and_takes_only_bools():
    feature = EventSynchronization(window=10)
    feature._block
    feature.weighted = True
    assert feature.weighted is True
    feature.weighted = False
    assert feature.weighted is False
    for word in ("off", "on", "yes", 1):
        with pytest.raises(TypeError, match="True or False"):
            feature.weighted = word


@pytest.mark.parametrize("cls, method", [(Rarity, "mode-distance"), (Symmetry, "Reflection")])
def test_method_feature_takes_a_string(cls, method):
    kwargs = {"window": 10} if cls is Rarity else {"joint_pairs": [(0, 1)]}
    assert cls(method=method, **kwargs).method == method.lower().replace("-", "_")


@pytest.mark.parametrize("cls", [Rarity, Symmetry])
def test_method_feature_rejects_an_unknown_string(cls):
    with pytest.raises(ValueError, match="method") as error:
        cls(method="nonsense")
    assert "'reflection'" in str(error.value) or "'mode_distance'" in str(error.value)




def test_a_list_of_choices_reads_back_as_a_list_and_one_choice_as_a_string():
    assert Kinematics(output_type=["Velocity", "acceleration"]).output_type == ["velocity", "acceleration"]
    assert Kinematics(output_type=("velocity",)).output_type == ["velocity"]
    assert Kinematics(output_type="Acceleration").output_type == "acceleration"


def test_a_wrong_element_of_a_list_of_choices_lists_the_options():
    with pytest.raises(ValueError, match="output_type") as error:
        Kinematics(output_type=["velocity", "speed"])
    assert "'speed'" in str(error.value) and "'direction'" in str(error.value)


def test_a_list_of_enum_members_and_strings_is_taken():
    types = core.trajectory.KinematicsOutputType
    assert Kinematics(output_type=[types.JERK, "smoothed"]).output_type == ["jerk", "smoothed"]


def test_the_list_of_choices_is_assigned_by_the_setter_and_changes_the_outputs():
    feature = Kinematics(dims=2)
    feature.output_type = ["velocity", "acceleration"]
    assert feature.outputs.names == ("velocity", "acceleration")
    feature.output_type = "jerk"
    assert feature.outputs.names == ("jerk",)
    with pytest.raises(ValueError, match="output_type"):
        feature.output_type = ["jerk", "nonsense"]
    assert feature.outputs.names == ("jerk",)


@pytest.mark.parametrize("types", [[], ["velocity", "velocity"]])
def test_no_output_or_a_repeated_one_raises_at_construction(types):
    with pytest.raises(ValueError):
        Kinematics(dims=2, output_type=types)
