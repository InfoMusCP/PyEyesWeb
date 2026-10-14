"""Live parameter changes of the humanoid / mass-spring features (checks in `tests/_support/live_param_suite.py`).

Every block of this area keeps a physical state (masses, velocities, the estimated parameters), so a changed parameter is
compared with the raw core block that adopts the new parameters at the same frame (`adopt_params`): the numbers are the
block's, bit for bit, and the result says "parameters changed: state reset" exactly when the block reports that it
forgot its state. The classification is the core's, from the original (see the headers of the blocks):

* `HumanoidSimulator`, `GenericModelSimulator`, `GenericModelPredictor`: every parameter is LIVE; the topology of a
  model (names of its masses and springs, which end masses) is STRUCTURAL, the rest of a model is LIVE.
* `GenericModelEstimator`: LIVE except `seed` and the topology of the model.
* `HumanoidOrientations`: `reference_direction` is STRUCTURAL (the body is built from it).
"""

import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
pytest.importorskip("pyeyesweb._core", exc_type=ImportError)

from humanoid_inputs import CHAIN_XML, REFERENCE, forearm  # noqa: E402
from live_param_suite import CHANGE_AT, NOTE, check_invalid, check_structural, feed  # noqa: E402

from pyeyesweb._core import core  # noqa: E402
from pyeyesweb.physical_signals import (HUMANOID_JOINTS, GenericModelEstimator, GenericModelPredictor,  # noqa: E402
                                        GenericModelSimulator, HumanoidOrientations, HumanoidSimulator, MassSpringModel)

RAW = core.humanoid
DT = 0.04
RATE = dict(sampling_rate=25.0, units="mm")  # the time and the unit these frames are in
MODEL = MassSpringModel.from_xml_string(CHAIN_XML)
RAW_MODEL = RAW.MassSpringModel.from_xml_string(CHAIN_XML)
FOREARM = forearm(120, noise=3.0, seed=4)
CHAIN_DIRECTIONS = REFERENCE["bone_directions"]
CHAIN_POSITIONS = REFERENCE["model_positions"]
JOINT_LAYOUT = core.SkeletonLayout(list(HUMANOID_JOINTS))
SPRING_LAYOUT = core.SkeletonLayout([str(label) for label in REFERENCE["spring_labels"]])
MASS_LAYOUT = core.SkeletonLayout([str(label) for label in REFERENCE["mass_labels"]])


def _raw(params):
    """The keywords of the raw block: it spells the reference direction as the core does."""
    return {"ref_dir" if name == "reference_direction" else name: value for name, value in params.items()}


def _positions(output):
    return output[0] if isinstance(output, tuple) else output


# name -> (feature factory, raw factory, layout, frames); the raw factory takes the changed parameters as keywords
BLOCKS = {
    "HumanoidSimulator": (lambda **params: HumanoidSimulator(**RATE, **params), lambda **params: RAW.HumanoidSimulator(**_raw(params)),
                          JOINT_LAYOUT, FOREARM),
    "GenericModelSimulator": (lambda **params: GenericModelSimulator(MODEL, **RATE, **params),
                              lambda **params: RAW.GenericModelSimulator(RAW_MODEL, **_raw(params)), SPRING_LAYOUT, CHAIN_DIRECTIONS),
    "GenericModelPredictor": (lambda **params: GenericModelPredictor(MODEL, **RATE, **params),
                              lambda **params: RAW.GenericModelPredictor(RAW_MODEL, **_raw(params)), SPRING_LAYOUT, CHAIN_DIRECTIONS),
    "GenericModelEstimator": (lambda **params: GenericModelEstimator(MODEL, estimate_direction_springs=True, **RATE, **params),
                              lambda **params: RAW.GenericModelEstimator(RAW_MODEL, **_raw({"estimate_direction_springs": True, **params})),
                              MASS_LAYOUT, CHAIN_POSITIONS),
}

COMMON = [("damping", 3.0), ("viscosity", 2.0), ("gravity", (0.0, -500.0, 0.0)), ("length_forces", False),
          ("rotation_forces", False), ("integration_step", 0.002), ("reference_direction", (0.0, 0.0, 1.0)),
          ("floor_position", (0.0, -1.0, 0.0)), ("ground_interaction", True)]
GENERIC = [("use_input_lengths", True)]
CASES = (
    [("HumanoidSimulator", name, value, False) for name, value in COMMON]
    + [("GenericModelSimulator", name, value, False) for name, value in COMMON + GENERIC]
    + [("GenericModelPredictor", name, value, False) for name, value in COMMON + GENERIC + [
        ("prediction_interval", 0.5), ("damping_factor", 0.5), ("viscosity_factor", 2.0), ("mode", "directions_linear")]]
    + [("GenericModelEstimator", name, value, False) for name, value in COMMON + GENERIC + [
        ("enable_adaptation", False), ("estimate_masses", True), ("estimate_length_springs", True),
        ("estimate_direction_springs", False), ("step_is_absolute", True), ("initial_step", 0.1),
        ("step_adaptation_factor", 0.001), ("cost_distance", 2.0), ("cost_directions", 2.0), ("cost_speed", 2.0),
        ("cost_length_stiffness", 0.5), ("cost_direction_stiffness", 0.5), ("cost_length_damping", 0.5),
        ("cost_direction_damping", 0.5)]]
    + [("GenericModelEstimator", "seed", 99, True)]
)


def _raw_value(value):
    return RAW.PredictionMode.__members__[value.upper()] if value in ("directions_linear", "masses_inertia") else value


@pytest.mark.parametrize("block, attr, value, structural", CASES, ids=[f"{case[0]}.{case[1]}" for case in CASES])
def test_a_changed_parameter_is_what_the_raw_block_adopts(block, attr, value, structural):
    make_feature, make_raw, layout, frames = BLOCKS[block]
    feature, raw = make_feature(), make_raw()
    for index, frame in enumerate(frames):
        if index == CHANGE_AT:
            setattr(feature, attr, value)
            assert raw.adopt_params(make_raw(**{attr: _raw_value(value)})) is structural
        out = raw.process_array(layout, frame, DT)
        result = feature.process(frame)
        name = result.schema.names[0]
        assert np.array_equal(result[name], _positions(out), equal_nan=True), (attr, index)
        assert (NOTE in result.reason) is (structural and index == CHANGE_AT), (attr, index)
        assert result.status.name == "OK"


def test_a_model_of_the_same_topology_is_live_and_another_is_structural():
    softer = MassSpringModel.from_xml_string(CHAIN_XML)
    softer.set_parameter("spring::s1::stiffness", 10.0)
    feature, raw = GenericModelSimulator(MODEL, **RATE), RAW.GenericModelSimulator(RAW_MODEL)
    for index, frame in enumerate(CHAIN_DIRECTIONS[:CHANGE_AT + 5]):
        if index == CHANGE_AT:
            feature.model = softer
            assert raw.adopt_params(RAW.GenericModelSimulator(softer._model)) is False
        result = feature.process(frame)
        assert np.array_equal(result["positions"], raw.process_array(SPRING_LAYOUT, frame, DT), equal_nan=True)
        assert NOTE not in result.reason
    check_structural(lambda: GenericModelSimulator(MODEL, **RATE), "model",
                     MassSpringModel.from_xml_string(CHAIN_XML.replace('name="c"', 'name="d"').replace('mass2="c"', 'mass2="d"')),
                     list(CHAIN_DIRECTIONS))


def test_the_reference_direction_of_the_orientations_is_structural():
    check_structural(lambda: HumanoidOrientations(), "reference_direction", (0.0, 0.0, 1.0), list(FOREARM))


def test_the_sampling_rate_is_live():
    frames = FOREARM
    feature, raw = HumanoidSimulator(**RATE), RAW.HumanoidSimulator()
    for index, frame in enumerate(frames[:90]):
        if index == CHANGE_AT:
            feature.sampling_rate = 50.0
        out = raw.process_array(JOINT_LAYOUT, frame, DT if index < CHANGE_AT else 0.02)
        result = feature.process(frame)
        assert np.array_equal(result["joints"], out) and NOTE not in result.reason


def test_a_live_change_keeps_the_state_a_control_does_not_share():
    control, changed = HumanoidSimulator(**RATE), HumanoidSimulator(**RATE)
    before = feed(control, list(FOREARM[:CHANGE_AT])), feed(changed, list(FOREARM[:CHANGE_AT]))
    assert before[0] == before[1]
    changed.damping = 3.0
    assert feed(changed, list(FOREARM[CHANGE_AT:CHANGE_AT + 5])) != feed(control, list(FOREARM[CHANGE_AT:CHANGE_AT + 5]))


INVALID = [
    (lambda: HumanoidSimulator(integration_step=0.002, **RATE), "integration_step", 0.0, list(FOREARM)),
    (lambda: GenericModelSimulator(MODEL, integration_step=0.002, **RATE), "integration_step", -1.0, list(CHAIN_DIRECTIONS)),
    (lambda: GenericModelPredictor(MODEL, prediction_interval=0.2, **RATE), "prediction_interval", -0.1, list(CHAIN_DIRECTIONS)),
    (lambda: GenericModelPredictor(MODEL, mode="masses_inertia", **RATE), "mode", "sideways", list(CHAIN_DIRECTIONS)),
    (lambda: GenericModelEstimator(MODEL, initial_step=0.05, **RATE), "initial_step", -1.0, list(CHAIN_POSITIONS)),
    (lambda: GenericModelSimulator(MODEL, length_forces=True, **RATE), "length_forces", "yes", list(CHAIN_DIRECTIONS)),
]


@pytest.mark.parametrize("factory, attr, value, recording", INVALID, ids=[f"{row[1]}-{index}" for index, row in enumerate(INVALID)])
def test_a_bad_value_raises_at_the_setter_and_changes_nothing(factory, attr, value, recording):
    if isinstance(value, str) and value == "yes":
        feature = factory()
        with pytest.raises(TypeError):
            setattr(feature, attr, value)
        return
    check_invalid(factory, attr, value, recording)
