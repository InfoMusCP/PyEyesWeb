"""Skeleton presets of the lab devices, `skeleton=` of the features and the guards against silent zeros."""

import dataclasses
from pathlib import Path

import numpy as np
import pytest

from pyeyesweb.data_models.results import Status
from pyeyesweb.low_level import KineticEnergy, PointsDensity, Symmetry
from pyeyesweb.low_level import MotionNoiseDetector
from pyeyesweb.skeletons import KINECT_V2, MEDIAPIPE, OPENPOSE, QUALISYS_SPORT, SKELETON_TODO, SKELETONS, Skeleton, \
    get_skeleton

TSV = Path(__file__).resolve().parents[2] / "examples" / "data" / "qualisys" / "trial3.tsv"
NAMES = list(SKELETONS)
RNG = np.random.default_rng(3)


def _frames(skeleton, count=40):
    return RNG.normal(size=(count, len(skeleton.joints), 3))


@pytest.mark.parametrize("name", NAMES)
def test_every_preset_is_consistent(name):
    skeleton = SKELETONS[name]
    assert len(set(skeleton.joints)) == len(skeleton.joints)
    assert all(left in skeleton.joints and right in skeleton.joints and left != right
               for left, right in skeleton.pairs)
    assert skeleton.index(skeleton.joints[-1]) == len(skeleton.joints) - 1
    if skeleton.weights is not None:
        assert set(skeleton.weights) == set(skeleton.joints)


def test_preset_sizes():
    assert [len(skeleton.joints) for skeleton in (KINECT_V2, QUALISYS_SPORT, MEDIAPIPE, OPENPOSE)] == [25, 41, 33, 25]


def test_qualisys_names_are_the_tsv_headers():
    header = next(line for line in TSV.read_text().splitlines() if line.startswith("MARKER_NAMES"))
    assert list(QUALISYS_SPORT.joints) == header.split("\t")[1:]


def test_missing_reports_what_is_none():
    assert SKELETON_TODO == {name: SKELETONS[name].missing() for name in NAMES}
    assert KINECT_V2.missing() == ()
    assert QUALISYS_SPORT.missing() == ("reference", "weights")
    assert MEDIAPIPE.missing() == ("reference", "weights")
    assert OPENPOSE.missing() == ("weights",)
    bare = Skeleton("bare", ("a", "b"))
    assert bare.missing() == ("pairs", "reference", "weights")
    assert bare.weights_or_uniform() == {"a": 1.0, "b": 1.0}


def test_skeleton_is_frozen_and_validated():
    with pytest.raises(dataclasses.FrozenInstanceError):
        KINECT_V2.name = "other"
    with pytest.raises(ValueError, match="repeated"):
        Skeleton("bad", ("a", "a"))
    with pytest.raises(ValueError, match="not joints"):
        Skeleton("bad", ("a", "b"), pairs=(("a", "c"),))


def test_get_skeleton_accepts_names_and_instances():
    assert get_skeleton("Kinect-V2") is KINECT_V2
    assert get_skeleton("qualisys sport") is QUALISYS_SPORT
    assert get_skeleton(OPENPOSE) is OPENPOSE
    with pytest.raises(ValueError, match="kinect_v2.*qualisys_sport.*mediapipe.*openpose"):
        get_skeleton("kinect")


@pytest.mark.parametrize("name", NAMES)
def test_kinetic_energy_with_a_skeleton(name):
    skeleton = SKELETONS[name]
    feature = KineticEnergy(skeleton=name)
    assert feature.inputs[0].labels == skeleton.joints
    energy = feature.run(_frames(skeleton))["kinetic_energy"]
    assert np.isfinite(energy).all() and energy[1:].min() > 0


def test_kinetic_energy_explicit_parameters_win():
    feature = KineticEnergy(skeleton="mediapipe", labels=["a", "b"], weights={"a": 2.0})
    assert feature.inputs[0].labels == ("a", "b")
    feature = KineticEnergy(skeleton="mediapipe", weights={"nose": 1.0})
    energy = feature.run(_frames(MEDIAPIPE))["kinetic_energy"]
    uniform = KineticEnergy(skeleton="mediapipe").run(_frames(MEDIAPIPE))["kinetic_energy"]
    assert energy[1:].min() > 0 and not np.allclose(energy, uniform)


@pytest.mark.parametrize("name", NAMES)
def test_motion_noise_detector_with_a_skeleton(name):
    skeleton = SKELETONS[name]
    detector = MotionNoiseDetector(skeleton=name)
    assert detector.inputs[0].labels == skeleton.joints
    results = [detector.process(frame, timestamp=0.04 * (index + 1)) for index, frame in enumerate(_frames(skeleton, 12))]
    assert all(result.status is Status.OK and result.is_noisy is False for result in results)  # too few speeds for a verdict


@pytest.mark.parametrize("name", NAMES)
def test_symmetry_with_a_skeleton(name):
    skeleton = SKELETONS[name]
    reference = {} if skeleton.reference else {"reference_point": skeleton.joints[0]}  # a preset without one needs it given
    result = Symmetry(skeleton=name, **reference).process(_frames(skeleton, 1)[0])
    assert result.status is Status.OK
    assert np.isfinite(result.symmetry) and result.symmetry > 0


def test_symmetry_explicit_pairs_win_and_reflection_takes_the_skeleton_too():
    pairs = [("LHeelBack", "RHeelBack")]
    feature = Symmetry(skeleton="qualisys_sport", pairs=pairs, reference_point=QUALISYS_SPORT.joints[0])
    assert feature.process(_frames(QUALISYS_SPORT, 1)[0]).status is Status.OK
    mirror = Symmetry(method="reflection", skeleton="qualisys_sport", pairs=pairs)
    assert mirror.process(_frames(QUALISYS_SPORT, 1)[0]).status is Status.OK


@pytest.mark.parametrize("name", NAMES)
def test_points_density_takes_the_joints(name):
    skeleton = SKELETONS[name]
    feature = PointsDensity(skeleton=name)
    assert feature.inputs[0].labels == skeleton.joints
    assert feature.process(_frames(skeleton, 1)[0]).status is Status.OK


@pytest.mark.parametrize("make", [
    lambda: KineticEnergy(),
    lambda: MotionNoiseDetector(),
    lambda: Symmetry(),
    lambda: Symmetry(labels=["a", "b"]),
])
def test_without_skeleton_information_the_constructor_raises(make):
    with pytest.raises(ValueError, match="no joints given"):
        make()


def test_kinetic_energy_labels_alone_weigh_every_joint_one_and_a_missing_joint_zero():
    assert KineticEnergy(labels=["a", "b"]).parameters["weights"] == {"a": 1.0, "b": 1.0}
    frames = np.zeros((2, 2, 3))
    frames[1, :, 0] = 1.0
    both = KineticEnergy(labels=["a", "b"]).run(frames).kinetic_energy
    only_a = KineticEnergy(labels=["a", "b"], weights={"a": 1.0}).run(frames).kinetic_energy
    np.testing.assert_allclose(both, [0.0, 1.0])
    np.testing.assert_allclose(only_a, [0.0, 0.5])


@pytest.mark.parametrize("make, key", [
    (lambda: KineticEnergy(labels=["a", "b"], weights={"a": 1.0, "c": 1.0}), "c"),
    (lambda: Symmetry(labels=["a", "b"], pairs=[("a", "z")]), "z"),
])
def test_names_not_among_the_labels_raise(make, key):
    with pytest.raises(ValueError, match=key):
        make()


def test_a_custom_configuration_with_a_foreign_frame_is_invalid_input():
    """Without configured labels a frame without the joints is missing them (`INVALID_INPUT`); with labels, a joint name
    that is not one of them is a configuration error (`ValueError`)."""
    frame = {"x": (0, 0, 0), "y": (1, 1, 1)}
    ke = KineticEnergy(weights={"a": 1.0, "b": 1.0})
    assert ke.process(frame).reason == "missing joints: a, b"
    detector = MotionNoiseDetector(labels=["a", "b"])
    with pytest.raises(ValueError, match="unknown joint names"):
        detector.process(frame, timestamp=0.0)
    assert detector.process({"a": (0, 0, 0)}).reason == "missing joints: b"
    assert Symmetry(pairs=[("a", "b")]).process(frame).status is Status.INVALID_INPUT
    assert ke.process({"a": (0, 0, 0), "b": (1, 1, 1)}).status is Status.OK
