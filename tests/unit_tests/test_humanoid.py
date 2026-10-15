"""The humanoid / mass-spring features (EyesWeb HumanoidModel): call contract, joint maps, errors and parity with the raw core
blocks (bit for bit) and with the frozen output of the colleague's port (`tests/data/humanoid_reference.npz`).
Needs the compiled core (EYESWEB_CORE_PATH), else skipped."""
import os
import sys

import numpy as np
import pytest

if os.environ.get("EYESWEB_CORE_PATH"):
    sys.path.insert(0, os.environ["EYESWEB_CORE_PATH"])
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

pytest.importorskip("pyeyesweb._core", exc_type=ImportError)

from contract_suite import check_feature_contract  # noqa: E402
from humanoid_inputs import CHAIN_XML, MASSES, REFERENCE, SPRINGS, forearm, tpose  # noqa: E402
from pyeyesweb import Layer, catalog  # noqa: E402
from pyeyesweb._core import core  # noqa: E402
from pyeyesweb.data_models import Status  # noqa: E402
from pyeyesweb.physical_signals import (HUMANOID_BONES, HUMANOID_JOINTS, GenericModelEstimator, GenericModelOrientations,  # noqa: E402
                                        GenericModelPredictor, GenericModelSimulator, HumanoidOrientations,
                                        HumanoidSimulator, MassSpringModel, PointsPredictor)

DT = 0.04
RATE = 25.0
MM = dict(sampling_rate=RATE, units="mm")  # the frame rate and the unit of the test frames
RAW = core.humanoid
JOINT_LAYOUT = core.SkeletonLayout(list(HUMANOID_JOINTS))
MODEL = MassSpringModel.from_xml_string(CHAIN_XML)
CHAIN_POSITIONS = REFERENCE["model_positions"]
CHAIN_DIRECTIONS = REFERENCE["bone_directions"]


def _same(left, right):
    return np.array_equal(np.asarray(left), np.asarray(right), equal_nan=True)


def _stream(feature, *recordings):
    return [feature.process(*(recording[index] for recording in recordings)) for index in range(len(recordings[0]))]


def _stack(results, name):
    return np.stack([result[name] for result in results])


def _with_missing(frames):
    """Frames in which one joint drops out now and then and one never is seen."""
    frames = frames.copy()
    frames[::3, HUMANOID_JOINTS.index("right_hand")] = np.nan
    frames[:, HUMANOID_JOINTS.index("left_foot")] = np.nan
    return frames


SCENARIOS = {
    "tpose": np.repeat(tpose()[None], 30, axis=0),
    "forearm": forearm(80),
    "forearm_noisy": forearm(80, noise=10.0, seed=3),
    "missing_joints": _with_missing(forearm(60)),
}


@pytest.mark.parametrize("scenario", SCENARIOS)
def test_humanoid_simulator_is_the_raw_block(scenario):
    frames = SCENARIOS[scenario]
    raw = RAW.HumanoidSimulator()
    expected = np.stack([raw.process_array(JOINT_LAYOUT, frame, DT) for frame in frames])
    results = _stream(HumanoidSimulator(**MM), frames)
    assert all(result.status is Status.OK for result in results)
    assert _same(_stack(results, "joints"), expected)
    assert _same(HumanoidSimulator(**MM).run(frames)["joints"], expected)
    assert _same(HumanoidSimulator(**MM, labels=HUMANOID_JOINTS).run(frames)["joints"], expected)
    assert HumanoidSimulator(**MM).outputs["joints"].axis_names[0] == tuple(raw.output_labels)


@pytest.mark.parametrize("scenario", SCENARIOS)
def test_humanoid_orientations_is_the_raw_block(scenario):
    frames = SCENARIOS[scenario]
    expected = RAW.HumanoidOrientationsExtractor().run(JOINT_LAYOUT, frames)
    assert _same(HumanoidOrientations().run(frames)["directions"], expected)
    assert _same(_stack(_stream(HumanoidOrientations(), frames), "directions"), expected)


def test_humanoid_simulator_with_control_is_the_raw_block_through_the_pipeline():
    frames = forearm(60, noise=5.0, seed=1)
    controls = HumanoidOrientations().run(frames)["directions"]
    raw, extractor = RAW.HumanoidSimulator(), RAW.HumanoidOrientationsExtractor()
    expected = []
    for frame in frames:
        joints = {name: tuple(row) for name, row in zip(HUMANOID_JOINTS, frame)}
        out = raw.process(joints, DT, extractor.process(joints))
        expected.append([out[name] for name in raw.output_labels])
    results = _stream(HumanoidSimulator(**MM), frames, controls)
    assert _same(_stack(results, "joints"), np.array(expected))
    assert _same(HumanoidSimulator(**MM).run(frames, controls)["joints"], np.array(expected))
    as_dicts = [{bone: tuple(row) for bone, row in zip(HUMANOID_BONES, control)} for control in controls]
    feature = HumanoidSimulator(**MM)
    assert _same([feature.process(frame, control)["joints"] for frame, control in zip(frames, as_dicts)], np.array(expected))


def _qualisys_excerpt():
    """A Qualisys excerpt (mm) with the shoulder centre appended, its labels and the `joint_map` onto the model."""
    excerpt = np.load(os.path.join(os.path.dirname(__file__), "..", "data", "motion_excerpts.npz"))
    labels = [str(name) for name in excerpt["names"]] + ["Shoulder_Center"]
    frames = excerpt["trial20"]
    frames = np.concatenate([frames, ((frames[:, labels.index("Left_Shoulder")] + frames[:, labels.index("Right_Shoulder")]) / 2)[:, None]], axis=1)
    joint_map = {"head": "Head", "neck": "Neck", "spine": "Spine", "spine_base": "Pelvis", "spine_shoulder": "Shoulder_Center",
                 **{f"{side}_{part}": f"{side.capitalize()}_{part.capitalize()}"
                    for side in ("left", "right") for part in ("shoulder", "elbow", "wrist", "hand", "hip", "knee", "ankle", "foot")}}
    return frames, labels, joint_map


@pytest.mark.parametrize("case", ["tpose", "forearm", "qualisys"])
def test_the_extractor_output_as_control_gives_the_pose_of_the_joints(case):
    """Round trip: joints -> `HumanoidOrientations` -> `control` of a simulator, against the simulator driven by the joints
    themselves. The simulator only reads the target bone directions, so equal simulated joints (max absolute difference over
    the first 30 frames, mm) mean equal target directions. Rounding differences (1e-13) grow exponentially in the flutter of the
    model (a 1e-14 perturbation of the input does the same), so a longer comparison would test the dynamics, not the control."""
    kwargs, mapping = {}, {}
    if case == "qualisys":
        frames, labels, joint_map = _qualisys_excerpt()
        mapping, kwargs = dict(labels=labels, joint_map=joint_map), dict(start_from_input=True)
    else:
        frames = SCENARIOS[case]
    frames = frames[:30]
    controls = HumanoidOrientations(**mapping).run(frames)["directions"]
    driven_by_joints = HumanoidSimulator(**MM, **mapping, **kwargs).run(frames)["joints"]
    driven_by_control = HumanoidSimulator(**MM, **mapping, **kwargs).run(frames, controls)["joints"]
    assert np.abs(driven_by_control - driven_by_joints).max() < 1e-9


def test_control_directions_are_relative_to_the_parent_bone():
    """Turning the upper arm turns the forearm with it: the same relative control gives another world pose."""
    pose = tpose()
    straight = HumanoidOrientations().run(pose[None])["directions"]
    bent = pose.copy()
    shoulder = bent[HUMANOID_JOINTS.index("left_shoulder")]
    moving = [HUMANOID_JOINTS.index(name) for name in ("left_elbow", "left_wrist", "left_hand")]
    bent[moving] = shoulder + (bent[moving] - shoulder) @ np.array([[0, -1, 0], [1, 0, 0], [0, 0, 1.0]]).T  # upper arm turned 90 degrees
    turned = HumanoidOrientations().run(bent[None])["directions"]
    forearm_index = HUMANOID_BONES.index("left_elbow-left_wrist")
    assert np.allclose(turned[0, forearm_index], straight[0, forearm_index])  # the forearm did not change in the parent's frame
    controlled = HumanoidSimulator(**MM, start_from_input=True).run(np.repeat(bent[None], 400, axis=0), np.repeat(turned, 400, axis=0))["joints"][-1]
    wrist, elbow = (controlled[HUMANOID_JOINTS.index(name)] for name in ("left_wrist", "left_elbow"))
    assert np.allclose((wrist - elbow) / np.linalg.norm(wrist - elbow), (bent[moving[1]] - bent[moving[0]]) / np.linalg.norm(bent[moving[1]] - bent[moving[0]]), atol=1e-3)


def test_humanoid_reset_goes_back_to_the_tpose():
    frames = forearm(40)
    feature = HumanoidSimulator(**MM)
    first = _stack(_stream(feature, frames), "joints")
    feature.reset()
    assert _same(_stack(_stream(feature, frames), "joints"), first)


def test_humanoid_blocks_reproduce_the_frozen_reference():
    joints = REFERENCE["joints"]
    assert _same(HumanoidSimulator(**MM).run(joints)["joints"], REFERENCE["humanoid_simulated"]) or \
        np.abs(HumanoidSimulator(**MM).run(joints)["joints"] - REFERENCE["humanoid_simulated"]).max() < 1e-9
    orientations = HumanoidOrientations().run(joints)["directions"]
    assert np.abs(orientations - REFERENCE["orientations"]).max() < 1e-9
    controlled = HumanoidSimulator(**MM).run(joints, orientations)["joints"]
    assert np.abs(controlled - REFERENCE["humanoid_control_simulated"]).max() < 1e-9


def test_generic_blocks_reproduce_the_frozen_reference():
    assert tuple(MODEL.mass_names) == MASSES and tuple(MODEL.spring_names) == SPRINGS
    assert np.abs(GenericModelOrientations(MODEL).run(CHAIN_POSITIONS)["directions"] - CHAIN_DIRECTIONS).max() < 1e-9
    assert np.abs(GenericModelSimulator(MODEL, **MM).run(CHAIN_DIRECTIONS)["positions"] - REFERENCE["generic_simulated"]).max() < 1e-9
    for mode, key in (("masses_inertia", "predicted_inertia"), ("directions_linear", "predicted_linear")):
        predicted = GenericModelPredictor(MODEL, **MM, mode=mode, damping_factor=0.7).run(CHAIN_DIRECTIONS)["positions"]
        assert np.abs(predicted - REFERENCE[key]).max() < 1e-9
    estimator = GenericModelEstimator(MODEL, **MM, enable_adaptation=False).run(CHAIN_POSITIONS)
    assert np.abs(estimator["positions"] - REFERENCE["estimated_positions"]).max() < 1e-9
    assert np.abs(estimator["error"] - REFERENCE["estimated_errors"]).max() < 1e-9
    assert np.abs(PointsPredictor(labels=MASSES).run(CHAIN_POSITIONS)["predicted"] - REFERENCE["points_predicted"]).max() < 1e-9


def test_generic_blocks_are_the_raw_blocks():
    core_model = RAW.MassSpringModel.from_xml_string(CHAIN_XML)
    layout = core.SkeletonLayout(list(MASSES))
    spring_layout = core.SkeletonLayout(list(SPRINGS))
    assert _same(GenericModelOrientations(MODEL).run(CHAIN_POSITIONS)["directions"],
                 RAW.GenericModelOrientationsExtractor(core_model).run(layout, CHAIN_POSITIONS))
    for mode in ("masses_inertia", "directions_linear"):
        raw = RAW.GenericModelPredictor(core_model, mode=RAW.PredictionMode.__members__[mode.upper()], prediction_interval=0.3)
        feature = GenericModelPredictor(MODEL, **MM, mode=mode, prediction_interval=0.3)
        assert _same(feature.run(CHAIN_DIRECTIONS)["positions"], raw.run(spring_layout, CHAIN_DIRECTIONS, dt=DT))
    raw_estimator = RAW.GenericModelEstimator(core_model, estimate_direction_springs=True, seed=5)
    positions, errors = raw_estimator.run(layout, CHAIN_POSITIONS, dt=DT)
    recorded = GenericModelEstimator(MODEL, **MM, estimate_direction_springs=True, seed=5).run(CHAIN_POSITIONS)
    assert _same(recorded["positions"], positions) and _same(recorded["error"], errors)
    assert _same(PointsPredictor(labels=MASSES).run(CHAIN_POSITIONS)["predicted"],
                 RAW.PointsPredictor().run(layout, CHAIN_POSITIONS))


FEATURES = {
    "HumanoidSimulator": (lambda: HumanoidSimulator(**MM), (forearm(30), HumanoidOrientations().run(forearm(30))["directions"])),
    "HumanoidOrientations": (lambda: HumanoidOrientations(), (forearm(30),)),
    "GenericModelOrientations": (lambda: GenericModelOrientations(MODEL), (CHAIN_POSITIONS[:30],)),
    "GenericModelSimulator": (lambda: GenericModelSimulator(MODEL, **MM), (CHAIN_DIRECTIONS[:30],)),
    "GenericModelPredictor": (lambda: GenericModelPredictor(MODEL, **MM), (CHAIN_DIRECTIONS[:30],)),
    "GenericModelEstimator": (lambda: GenericModelEstimator(MODEL, **MM, estimate_masses=True), (CHAIN_POSITIONS[:30],)),
    "PointsPredictor": (lambda: PointsPredictor(labels=MASSES), (CHAIN_POSITIONS[:30],)),
}


@pytest.mark.parametrize("name", FEATURES)
def test_feature_contract(name):
    factory, recordings = FEATURES[name]
    check_feature_contract(factory, *recordings)


def test_the_features_are_catalogued_as_physical_signals():
    found = {info.name: (info.layer, info.eyesweb_block) for info in catalog()}
    for name, block in (("HumanoidSimulator", "HumanoidSimulator (MassSpringHumanoidSimulator)"),
                        ("HumanoidOrientations", "HumanoidOrientationsExtractor"),
                        ("GenericModelOrientations", "GenericModelOrientationsExtractor"),
                        ("GenericModelSimulator", "GenericModelSimulator"), ("GenericModelPredictor", "GenericModelPredictor"),
                        ("GenericModelEstimator", "GenericModelEstimator"), ("PointsPredictor", "PointsPredictor")):
        assert found[name] == (Layer.PHYSICAL_SIGNALS, block)
    assert "MassSpringModel" not in found  # a helper, not a feature


def test_schemas_are_known_before_data():
    simulator = HumanoidSimulator(**MM)
    joints = simulator.outputs["joints"]
    assert joints.shape == (21, 3) and joints.axis_names == (HUMANOID_JOINTS, ("x", "y", "z")) and joints.unit == "mm"
    assert HumanoidOrientations().outputs["directions"].axis_names[0] == HUMANOID_BONES
    assert simulator.inputs["control"].optional and simulator.inputs["control"].labels == HUMANOID_BONES
    assert simulator.inputs["skeleton"].labels == HUMANOID_JOINTS
    assert HumanoidSimulator(**MM, labels=[f"j{index}" for index in range(30)] + list(HUMANOID_JOINTS)).inputs["skeleton"].shape == (51, 3)
    estimator = GenericModelEstimator(MODEL, **MM)
    assert estimator.outputs.names == ("positions", "error") and estimator.outputs["positions"].axis_names[0] == MASSES
    assert GenericModelSimulator(MODEL, **MM).inputs["directions"].labels == SPRINGS
    assert GenericModelOrientations(MODEL).outputs["directions"].axis_names[0] == SPRINGS
    assert PointsPredictor(labels=MASSES).outputs["predicted"].axis_names[0] == MASSES


# ------------------------------------------------------------------------------------------------------ joint map


def _renamed(frames, order):
    """Frames with their rows in the order `order` (indices) and the labels of a foreign device."""
    return frames[:, order], [f"Marker_{HUMANOID_JOINTS[index]}" for index in order]


def test_a_joint_map_reads_the_users_labels_in_any_order():
    frames = forearm(50, noise=4.0, seed=2)
    order = np.random.default_rng(0).permutation(21)
    shuffled, labels = _renamed(frames, order)
    joint_map = {name: f"Marker_{name}" for name in HUMANOID_JOINTS}
    expected = HumanoidSimulator(**MM).run(frames)["joints"]
    assert _same(HumanoidSimulator(**MM, labels=labels, joint_map=joint_map).run(shuffled)["joints"], expected)
    assert _same(HumanoidOrientations(labels=labels, joint_map=joint_map).run(shuffled)["directions"],
                 HumanoidOrientations().run(frames)["directions"])
    feature = HumanoidSimulator(**MM, labels=labels + ["extra"], joint_map=joint_map)  # labels the model does not use are ignored
    extra = np.concatenate([shuffled, np.full((50, 1, 3), 7.0)], axis=1)
    assert _same(feature.run(extra)["joints"], expected)


def test_a_dict_frame_is_read_by_the_mapped_labels():
    frames = forearm(20)
    joint_map = {name: f"Marker_{name}" for name in HUMANOID_JOINTS}
    from_dicts, from_arrays = HumanoidSimulator(**MM, joint_map=joint_map), HumanoidSimulator(**MM)
    for frame in frames:
        dictionary = {f"Marker_{name}": tuple(row) for name, row in zip(HUMANOID_JOINTS, frame)}
        dictionary["unrelated"] = (1.0, 2.0, 3.0)
        assert _same(from_dicts.process(dictionary)["joints"], from_arrays.process(frame)["joints"])
    partial = {f"Marker_{name}": tuple(row) for name, row in zip(HUMANOID_JOINTS, frames[0]) if name != "left_hand"}
    assert HumanoidSimulator(**MM, joint_map=joint_map).process(partial).status is Status.OK  # a missing joint is a dropout


def test_a_partial_joint_map_keeps_the_other_names():
    frames = forearm(15)
    labels = [name if name != "head" else "skull" for name in HUMANOID_JOINTS]
    assert _same(HumanoidSimulator(**MM, labels=labels, joint_map={"head": "skull"}).run(frames)["joints"],
                 HumanoidSimulator(**MM).run(frames)["joints"])


def test_labels_that_miss_a_joint_of_the_model_raise_at_construction():
    labels = [name for name in HUMANOID_JOINTS if name != "left_hand"]
    for feature in (HumanoidSimulator, HumanoidOrientations):
        with pytest.raises(ValueError, match="left_hand"):
            feature(labels=labels)
    with pytest.raises(ValueError, match="Marker_head"):
        HumanoidSimulator(**MM, labels=HUMANOID_JOINTS, joint_map={"head": "Marker_head"})
    with pytest.raises(ValueError, match="not model names"):
        HumanoidSimulator(**MM, joint_map={"skull": "head"})
    with pytest.raises(ValueError, match="a"):
        GenericModelSimulator(MODEL, **MM, labels=["s1", "s2"])
    with pytest.raises(ValueError, match="no points"):
        PointsPredictor()


def test_labels_and_joint_map_can_be_changed_and_a_bad_value_changes_nothing():
    feature = HumanoidSimulator(**MM)
    feature.joint_map = {name: f"Marker_{name}" for name in HUMANOID_JOINTS}
    feature.labels = [f"Marker_{name}" for name in HUMANOID_JOINTS]
    assert feature.inputs["skeleton"].labels[0].startswith("Marker_") and feature.joint_map["head"] == "Marker_head"
    with pytest.raises(ValueError):
        feature.labels = ["head"]
    with pytest.raises(ValueError):
        feature.joint_map = {"nothing": "head"}
    assert feature.labels[0].startswith("Marker_") and feature.joint_map["head"] == "Marker_head"


def test_the_generic_features_map_masses_and_springs():
    labels = [f"p_{name}" for name in MASSES[::-1]]
    positions = CHAIN_POSITIONS[:, ::-1]
    mapping = {name: f"p_{name}" for name in MASSES}
    assert _same(GenericModelOrientations(MODEL, labels=labels, joint_map=mapping).run(positions)["directions"],
                 GenericModelOrientations(MODEL).run(CHAIN_POSITIONS)["directions"])
    spring_labels = [f"b_{name}" for name in SPRINGS[::-1]]
    spring_map = {name: f"b_{name}" for name in SPRINGS}
    assert _same(GenericModelSimulator(MODEL, **MM, labels=spring_labels, joint_map=spring_map).run(CHAIN_DIRECTIONS[:, ::-1])["positions"],
                 GenericModelSimulator(MODEL, **MM).run(CHAIN_DIRECTIONS)["positions"])


# ------------------------------------------------------------------------------------------------- bad data


def test_wrong_shapes_raise():
    simulator = HumanoidSimulator(**MM)
    for bad in (np.ones((20, 3)), np.ones((21, 2)), np.ones(63), np.ones((2, 21, 3))):
        with pytest.raises(ValueError, match="HumanoidSimulator"):
            simulator.process(bad)
    with pytest.raises(ValueError, match="control"):
        simulator.process(tpose(), np.ones((19, 3)))
    with pytest.raises(ValueError, match="HumanoidSimulator"):
        simulator.run(np.ones((5, 20, 3)))
    with pytest.raises(ValueError, match="PointsPredictor"):
        PointsPredictor(labels=MASSES).process(np.ones((3, 3)))


def test_bad_data_is_invalid_input_not_an_exception():
    for feature in (HumanoidSimulator(**MM), HumanoidOrientations()):
        for frame, reason in ((np.full((21, 3), np.nan), "no joint"), (np.full((21, 3), np.inf), "infinite"),
                              (np.zeros((0, 3)), "empty"), ({}, "no joint"), ({"a": (0, 0, 0)}, "match none")):
            result = feature.process(frame)
            assert result.status is Status.INVALID_INPUT and reason in result.reason, (feature, reason)
            assert np.isnan(result[feature.outputs.names[0]]).all()
    for feature in (GenericModelSimulator(MODEL, **MM), GenericModelEstimator(MODEL, **MM), GenericModelOrientations(MODEL),
                    GenericModelPredictor(MODEL, **MM), PointsPredictor(labels=MASSES)):
        assert feature.process(np.full((len(feature.inputs[0].labels), 3), np.nan)).status is Status.INVALID_INPUT
    assert PointsPredictor(labels=MASSES).process(np.full((4, 3), np.inf)).status is Status.INVALID_INPUT


def test_an_invalid_frame_does_not_disturb_the_state():
    frames = forearm(30)
    clean, disturbed = HumanoidSimulator(**MM), HumanoidSimulator(**MM)
    expected = _stack(_stream(clean, frames), "joints")
    results = []
    for index, frame in enumerate(frames):
        if index in (5, 12):
            assert disturbed.process(np.full((21, 3), np.nan)).status is Status.INVALID_INPUT
        results.append(disturbed.process(frame))
    assert _same(_stack(results, "joints"), expected)


def test_a_missing_joint_is_a_dropout_the_block_handles():
    frames = _with_missing(forearm(30))
    result = HumanoidSimulator(**MM).run(frames)
    assert result.ok.all() and np.isfinite(result["joints"]).all()


# ----------------------------------------------------------------------------------------------------- time


def test_time_is_the_timestamp_then_the_sampling_rate_then_per_sample():
    frames = forearm(20)
    mm = dict(units="mm")
    by_rate = HumanoidSimulator(sampling_rate=50.0, **mm).run(frames)["joints"]
    by_stamp = HumanoidSimulator(sampling_rate=50.0, **mm).run(frames, timestamps=np.arange(1, 21) * 0.02)["joints"]
    assert not _same(by_rate, HumanoidSimulator(sampling_rate=RATE, **mm).run(frames)["joints"])
    # the first step of a timed run is 1 / sampling_rate (an absolute time is not a step), then the timestamp differences
    assert _same(by_stamp, by_rate)
    assert not _same(HumanoidSimulator(sampling_rate=50.0, **mm).run(frames, timestamps=np.arange(1, 21) * 0.04)["joints"], by_rate)
    # no time at all: the default is None, one second per call, and every result says so
    feature = HumanoidSimulator(**mm)
    assert feature.sampling_rate is None
    assert "no time given: per-sample derivatives" in feature.process(frames[0]).reason
    assert "per-sample" not in HumanoidSimulator(**MM).process(frames[0]).reason
    assert "per-sample" in HumanoidSimulator(**mm).process(frames[0], timestamp=0.04).reason  # the first timed step is per sample
    raw = RAW.HumanoidSimulator()
    assert _same(HumanoidSimulator(**mm).run(frames)["joints"],
                 np.stack([raw.process_array(JOINT_LAYOUT, frame, 1.0) for frame in frames]))


def test_every_time_stepped_feature_defaults_to_no_rate_and_says_so():
    for feature, frame in ((GenericModelSimulator(MODEL), CHAIN_DIRECTIONS[0]), (GenericModelPredictor(MODEL), CHAIN_DIRECTIONS[0]),
                           (GenericModelEstimator(MODEL), CHAIN_POSITIONS[0])):
        assert feature.sampling_rate is None
        assert "no time given: per-sample derivatives" in feature.process(frame).reason
    timed = GenericModelSimulator(MODEL, sampling_rate=25.0)
    assert "per-sample" not in timed.process(CHAIN_DIRECTIONS[0]).reason
    untimed = GenericModelSimulator(MODEL)
    assert "per-sample" in untimed.process(CHAIN_DIRECTIONS[0], timestamp=0.1).reason  # no previous timestamp: per sample
    assert "per-sample" not in untimed.process(CHAIN_DIRECTIONS[1], timestamp=0.2).reason


# --------------------------------------------------------------------------------------------------------- units


def test_units_mm_is_the_core_bit_for_bit_and_metres_are_the_same_motion():
    frames = forearm(60, noise=3.0, seed=2)
    kwargs = dict(sampling_rate=RATE, gravity=(0.0, -9810.0, 0.0), ground_interaction=True, floor_position=(0.0, -1500.0, 0.0))
    raw = RAW.HumanoidSimulator(gravity=kwargs["gravity"], ground_interaction=True, floor_position=kwargs["floor_position"])
    expected = np.stack([raw.process_array(JOINT_LAYOUT, frame, DT) for frame in frames])
    in_mm = HumanoidSimulator(units="mm", **kwargs).run(frames)["joints"]
    assert _same(in_mm, expected)  # nothing converted: the numbers of the core
    in_metres = HumanoidSimulator(units="m", **{**kwargs, "gravity": (0.0, -9.81, 0.0), "floor_position": (0.0, -1.5, 0.0)}
                                  ).run(frames / 1000.0)["joints"]
    # data * 1000 and joints / 1000 are the only extra operations (rounding of the scaling, amplified by the dynamics):
    # equal to the millimetre run scaled by 1/1000 within 1e-9 of the body size, not bit for bit
    assert np.abs(in_metres * 1000.0 - expected).max() < 1e-6


def test_the_outputs_name_the_unit_of_the_data():
    assert HumanoidSimulator().outputs["joints"].unit == "m"
    assert HumanoidSimulator(units="mm").outputs["joints"].unit == "mm"
    assert GenericModelSimulator(MODEL).outputs["positions"].unit == "m"
    assert GenericModelEstimator(MODEL, units="mm").outputs["positions"].unit == "mm"
    assert GenericModelPredictor(MODEL, units="mm").outputs["positions"].unit == "mm"
    for build in (lambda: HumanoidSimulator(units="cm"), lambda: GenericModelSimulator(MODEL, units="cm")):
        with pytest.raises(ValueError, match="units"):
            build()


def test_the_generic_models_run_in_their_own_unit_and_only_name_it():
    assert _same(GenericModelSimulator(MODEL, sampling_rate=RATE, units="m").run(CHAIN_DIRECTIONS)["positions"],
                 GenericModelSimulator(MODEL, sampling_rate=RATE, units="mm").run(CHAIN_DIRECTIONS)["positions"])


def test_a_timestamp_that_does_not_advance_is_invalid_input():
    feature = HumanoidSimulator(**MM)
    assert feature.process(tpose(), timestamp=1.0).status is Status.OK
    result = feature.process(tpose(), timestamp=0.5)
    assert result.status is Status.INVALID_INPUT and result.reason == "non-increasing timestamp"
    assert feature.process(tpose(), timestamp=1.04).status is Status.OK


@pytest.mark.parametrize("rate", [0, -5.0, float("nan"), "fast", True])
def test_an_invalid_sampling_rate_raises(rate):
    for build in (lambda: HumanoidSimulator(sampling_rate=rate), lambda: GenericModelSimulator(MODEL, sampling_rate=rate),
                  lambda: GenericModelPredictor(MODEL, sampling_rate=rate), lambda: GenericModelEstimator(MODEL, sampling_rate=rate)):
        with pytest.raises(ValueError, match="sampling_rate"):
            build()
    feature = HumanoidSimulator(**MM)
    with pytest.raises(ValueError, match="sampling_rate"):
        feature.sampling_rate = rate
    assert feature.sampling_rate == 25.0


# ----------------------------------------------------------------------------------------- start from input


def test_start_from_input_puts_the_model_on_the_first_frame():
    frames = forearm(20)
    feature = HumanoidSimulator(**MM, start_from_input=True)
    first = feature.process(frames[0])
    assert np.allclose(first.joints, frames[0])
    raw = RAW.HumanoidSimulator()
    expected = [raw.process_array(JOINT_LAYOUT, frames[0], DT, True)]
    expected += [raw.process_array(JOINT_LAYOUT, frame, DT) for frame in frames[1:]]
    assert _same(HumanoidSimulator(**MM, start_from_input=True).run(frames)["joints"], np.stack(expected))
    feature.reset()
    assert np.allclose(feature.process(frames[3])["joints"], frames[3])  # again after a reset
    assert not np.allclose(feature.process(frames[4])["joints"], frames[4])
    feature.start_from_input = False
    with pytest.raises(TypeError):
        feature.start_from_input = "yes"
    with pytest.raises(TypeError):
        HumanoidSimulator(**MM, start_from_input=1)
    chain = GenericModelSimulator(MODEL, **MM, start_from_input=True)
    assert chain.start_from_input and chain.process(CHAIN_DIRECTIONS[0]).status is Status.OK


# ------------------------------------------------------------------------------------------ the model


def test_the_model_can_be_given_as_a_file_or_a_wrapper_or_a_core_model(tmp_path):
    path = tmp_path / "chain.xml"
    path.write_text(CHAIN_XML)
    expected = GenericModelSimulator(MODEL, **MM).run(CHAIN_DIRECTIONS)["positions"]
    for given in (path, str(path), MassSpringModel.from_xml_file(path), RAW.MassSpringModel.from_xml_string(CHAIN_XML)):
        assert _same(GenericModelSimulator(given, **MM).run(CHAIN_DIRECTIONS)["positions"], expected)
    with pytest.raises(FileNotFoundError):
        GenericModelSimulator(tmp_path / "missing.xml")
    with pytest.raises(TypeError, match="model"):
        GenericModelSimulator(3)
    with pytest.raises(ValueError):
        MassSpringModel.from_xml_string("<Model/>")


def test_mass_spring_model_builds_by_hand_and_round_trips():
    model = MassSpringModel(name="pendulum")
    model.add_mass("root", 1e10)
    model.add_mass("bob", 1.0, (100.0, 0.0, 0.0))
    model.add_spring("rod", "root", "bob", 100.0, 1000.0, (1.0, 0.0, 0.0), 1000.0)
    assert model.mass_names == ["bob", "root"] and model.spring_names == ["rod"] and model.spring_masses("rod") == ("root", "bob")
    again = MassSpringModel.from_xml_string(model.to_xml())
    assert again.spring_names == ["rod"] and again.export_configuration()["spring::rod::stiffness"] == 1000.0
    assert model.set_parameter("mass::bob::mass", 2.0) and not model.set_parameter("mass::nothing::mass", 1.0)
    assert "2 masses, 1 springs" in repr(model)
    with pytest.raises(AttributeError):
        model.no_such_method
    feature = GenericModelSimulator(model, **MM)  # the feature copies the model
    model.set_parameter("mass::bob::mass", 5.0)
    assert feature.model.export_configuration()["mass::bob::mass"] == 2.0
    assert isinstance(feature.model, MassSpringModel)


def _damped_model(length_damping, dir_damping, tip_mass=1.0, stiffness=1000.0):
    model = MassSpringModel(name="chain")
    model.add_mass("root", 1e10)
    model.add_mass("a&b", tip_mass, (1.0, 0.0, 0.0))  # a name that XML escapes
    model.add_mass("tip", 2.5, (2.0, 0.0, 0.0))
    model.add_spring("s1", "root", "a&b", 1.0, stiffness, (1.0, 0.0, 0.0), 300.0, length_damping, dir_damping)
    model.add_spring("s2", "a&b", "tip", 1.0, 50.0, (0.0, 1.0, 0.0), 80.0, dir_damping, length_damping)
    return model


@pytest.mark.parametrize("damping", [(1.0, 1.0), (0.0, 0.0), (0.3, 2.7), (5.0, 0.01)])
def test_a_saved_model_reloads_to_the_same_configuration(damping, tmp_path):
    model = _damped_model(*damping)
    model.set_parameter("spring::s2::damping", 0.37)  # an absolute coefficient set by hand
    saved = model.export_configuration()
    for again in (MassSpringModel.from_xml_string(model.to_xml()), _saved_and_loaded(model, tmp_path)):
        assert again.mass_names == model.mass_names and again.spring_names == model.spring_names
        configuration = again.export_configuration()
        assert configuration.keys() == saved.keys()
        assert configuration == pytest.approx(saved, rel=1e-12, abs=0.0)


def _saved_and_loaded(model, tmp_path):
    model.save_xml_file(tmp_path / "model.xml")
    return MassSpringModel.from_xml_file(tmp_path / "model.xml")


def test_a_model_without_relative_damping_is_written_as_zero():
    model = _damped_model(1.0, 1.0, stiffness=0.0)
    assert MassSpringModel.from_xml_string(model.to_xml()).export_configuration()["spring::s1::damping"] == 0.0


def test_a_loaded_file_keeps_its_relative_damping():
    xml = ('<Model><Masses><Mass name="r" mass="1" x="0" y="0" z="0"/><Mass name="t" mass="4" x="1" y="0" z="0"/></Masses>'
           '<Springs><Spring name="s" mass1="r" mass2="t" restLength="1" lengthStiffness="100" lengthDamping="2" restDirX="1" '
           'restDirY="0" restDirZ="0" dirStiffness="400" dirDamping="0.5"/></Springs></Model>')
    configuration = MassSpringModel.from_xml_string(xml).export_configuration()
    assert configuration["spring::s::damping"] == pytest.approx(0.5 * (4 * 100) ** 0.5 * 2)  # 0.5 * sqrt(mass2 * k) * relative
    assert configuration["spring::s::dir_damping"] == pytest.approx(0.5 * (4 * 400) ** 0.5 * 0.5)


def test_the_model_is_a_structural_parameter():
    feature = GenericModelSimulator(MODEL, **MM)
    for frame in CHAIN_DIRECTIONS[:5]:
        feature.process(frame)
    softer = MassSpringModel.from_xml_string(CHAIN_XML)
    softer.set_parameter("spring::s1::stiffness", 10.0)
    feature.model = softer  # the same topology: the stiffness is live, the state is kept
    assert "state reset" not in feature.process(CHAIN_DIRECTIONS[5]).reason
    renamed = MassSpringModel.from_xml_string(CHAIN_XML.replace('name="c"', 'name="d"').replace('mass2="c"', 'mass2="d"'))
    feature.model = renamed  # another topology: structural, the outputs follow the new names
    result = feature.process(CHAIN_DIRECTIONS[6])
    assert "state reset" in result.reason and feature.outputs["positions"].axis_names[0] == ("a", "b", "d", "root")
    assert _same(result["positions"], GenericModelSimulator(renamed, **MM).process(CHAIN_DIRECTIONS[6])["positions"])
    feature = GenericModelSimulator(MODEL, **MM, labels=SPRINGS)
    other = MassSpringModel()
    other.add_mass("root", 1e10)
    other.add_mass("tip", 1.0, (1.0, 0.0, 0.0))
    other.add_spring("rod", "root", "tip", 1.0, 100.0, (1.0, 0.0, 0.0), 100.0)
    with pytest.raises(ValueError, match="rod"):  # the labels no longer fit: nothing changes
        feature.model = other
    assert feature.model.spring_names == ["s1", "s2", "s3"] and feature.inputs[0].labels == SPRINGS
    assert GenericModelSimulator(other, **MM, labels=["rod"]).outputs["positions"].axis_names[0] == ("root", "tip")


def test_the_estimator_estimates_and_is_reproducible():
    positions = CHAIN_POSITIONS
    first = GenericModelEstimator(MODEL, **MM, estimate_direction_springs=True, seed=11)
    again = GenericModelEstimator(MODEL, **MM, estimate_direction_springs=True, seed=11)
    other = GenericModelEstimator(MODEL, **MM, estimate_direction_springs=True, seed=12)
    recorded = first.run(positions)
    assert _same(recorded["positions"], again.run(positions)["positions"]) and not _same(recorded["positions"], other.run(positions)["positions"])
    assert recorded["error"][-1] < recorded["error"][0]
    assert first.model.export_configuration() != MODEL.export_configuration()  # the estimated model
    assert first.current_step < 0.05
    first.reset_step()
    assert first.current_step == 0.05
    assert first.seed == 11


def test_the_predictor_modes_differ_and_a_wrong_mode_names_the_options():
    inertia = GenericModelPredictor(MODEL, **MM, mode="masses_inertia").run(CHAIN_DIRECTIONS)["positions"]
    linear = GenericModelPredictor(MODEL, **MM, mode="directions-linear").run(CHAIN_DIRECTIONS)["positions"]
    assert not _same(inertia, linear)
    with pytest.raises(ValueError, match="masses_inertia"):
        GenericModelPredictor(MODEL, **MM, mode="wrong")


def test_points_predictor_extrapolates_and_handles_dropouts():
    labels = ["a", "b"]
    feature = PointsPredictor(labels=labels)
    assert _same(feature.process({"a": (1, 0, 0), "b": (0, 1, 0)})["predicted"], [[1, 0, 0], [0, 1, 0]])  # first sight: unchanged
    assert _same(feature.process({"a": (2, 0, 0), "b": (0, 3, 0)})["predicted"], [[3, 0, 0], [0, 5, 0]])
    result = feature.process({"a": (3, 0, 0)})  # b is missing
    assert _same(result.predicted, [[4, 0, 0], [np.nan] * 3])
    assert PointsPredictor(skeleton="mediapipe").labels[0] == "nose"
    with pytest.raises(ValueError, match="repeated"):
        PointsPredictor(labels=["a", "a"])


def test_unknown_parameters_are_type_errors_with_a_suggestion():
    with pytest.raises(TypeError, match="did you mean 'damping'"):
        HumanoidSimulator(**MM, dampin=3.0)
    with pytest.raises(TypeError, match="spine_names"):  # the joint names are `joint_map`
        HumanoidSimulator(**MM, spine_names=["a", "b", "c", "d", "e"])
    with pytest.raises(TypeError, match="did you mean 'estimate_masses'"):
        GenericModelEstimator(MODEL, **MM, estimate_mass=True)
