"""Wrong arguments must raise or report, never crash the interpreter or return inf / NaN as OK."""

import numpy as np
import pytest

from pyeyesweb.data_models import Status
from pyeyesweb.low_level import Kinematics, KineticEnergy
from pyeyesweb.low_level import average_curvature_3d
from pyeyesweb.low_level import MotionNoiseDetector

LABELS = ["a", "b", "c"]
FRAMES = np.random.default_rng(0).normal(size=(30, 3, 3))


# ----------------------------------------------------- strings and dicts where numbers are expected (was a crash)
@pytest.mark.parametrize("bad", ["x", "abc", b"xyz", {"x": 1}, [["a", "b", "c"]], [[1, 2, "3"]]])
def test_non_numeric_arguments_raise_instead_of_crashing(bad):
    with pytest.raises((TypeError, ValueError)):
        average_curvature_3d(bad)


def test_a_string_inside_a_skeleton_dict_raises():
    ke = KineticEnergy(weights={"head": 1.0})
    with pytest.raises(TypeError):
        ke.process({"head": "abc"})


def test_absurdly_deep_nesting_raises():
    deep = [1.0]
    for _ in range(50):
        deep = [deep]
    with pytest.raises(ValueError, match="nested"):
        average_curvature_3d(deep)


# ------------------------------------------------ blocks with a time step (was inf / NaN with OK without a timestamp)
def _auto_kinematics():
    return Kinematics(dims=3)


def _auto_energy():
    return KineticEnergy(labels=LABELS, weights=dict.fromkeys(LABELS, 1.0))


@pytest.mark.parametrize("make, data", [(_auto_kinematics, FRAMES[:, 0, :]), (_auto_energy, FRAMES),
                                        (lambda: MotionNoiseDetector(labels=LABELS), FRAMES)])
def test_missing_time_is_per_sample_not_infinity(make, data):
    # Without timestamps or sampling_rate the step is one sample: finite values, and the result says so.
    feature = make()
    rows = [feature.process(sample) for sample in data[:12]]
    assert all(result.status is not Status.INVALID_INPUT and "per-sample" in result.reason for result in rows)
    recorded = make().run(data)
    assert np.isfinite(np.asarray(recorded[recorded.schema.names[0]], dtype=float)).all()


@pytest.mark.parametrize("make, data", [(_auto_kinematics, FRAMES[:, 0, :]), (_auto_energy, FRAMES)])
def test_with_timestamps_the_values_are_finite(make, data):
    recorded = make().run(data, timestamps=np.arange(len(data)) * 0.02)
    column = np.asarray(recorded[recorded.schema.names[0]], dtype=float)
    assert np.isfinite(column[1:]).all()


def test_blocks_that_ignore_time_do_not_need_it():
    assert Kinematics(dims=3).process([0.0, 0.0, 0.0]).status is Status.OK
    assert KineticEnergy(labels=LABELS, weights=dict.fromkeys(LABELS, 1.0)).process(FRAMES[0]).status is Status.OK


# --------------------------------------------- weights that do not fit the joints (was the raw overload text of the core)
def test_weights_of_the_wrong_length_raise_a_clear_value_error():
    with pytest.raises(ValueError, match=r"weights has 1 value, the skeleton has 3 joints"):
        KineticEnergy(labels=LABELS, weights=[1.0])
    with pytest.raises(ValueError, match="weights must be a mapping"):
        KineticEnergy(weights=[1.0])  # no joint names to pair it with
    with pytest.raises(ValueError, match="weights must be a mapping"):
        KineticEnergy(labels=LABELS, weights="abc")


def test_a_sequence_of_weights_is_one_weight_per_label():
    by_list = KineticEnergy(labels=LABELS, weights=[1.0, 2.0, 3.0])
    by_name = KineticEnergy(labels=LABELS, weights=dict(zip(LABELS, [1.0, 2.0, 3.0])))
    stamps = np.arange(30) * 0.1
    assert np.array_equal(by_list.run(FRAMES, timestamps=stamps).kinetic_energy, by_name.run(FRAMES, timestamps=stamps).kinetic_energy)


# ----------------------------------------- an overflow is detected after the block advanced: pinned (DEVELOPMENT_SPEC, work package H)
def test_an_overflow_has_advanced_the_state_of_the_block():
    energy, control = (KineticEnergy(labels=["a"], weights={"a": 1.0}, sampling_rate=100.0) for _ in range(2))
    for feature in (energy, control):
        feature.process({"a": (0.0, 0.0, 0.0)}, timestamp=0.0)
    overflow = energy.process({"a": (1e300, 0.0, 0.0)}, timestamp=0.01)
    assert overflow.status is Status.INVALID_INPUT and overflow.reason == "the result is not finite"
    after = energy.process({"a": (0.01, 0.0, 0.0)}, timestamp=0.02)
    assert after.status is Status.INVALID_INPUT  # the block remembers 1e300 as the previous position
    assert control.process({"a": (0.01, 0.0, 0.0)}, timestamp=0.02).status is Status.OK


# ------------------------------------------------------------- timestamps that are not finite
@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -float("inf")])
@pytest.mark.parametrize("make, data", [(_auto_kinematics, FRAMES[0, 0, :]), (_auto_energy, FRAMES[0])])
def test_a_non_finite_timestamp_is_invalid_input_and_changes_nothing(make, data, bad):
    feature = make()
    rejected = feature.process(data, timestamp=bad)
    assert rejected.status is Status.INVALID_INPUT and rejected.reason == "non-finite timestamp"
    assert feature.process(data, timestamp=1.0).status is not Status.INVALID_INPUT  # the first timed call: nothing was remembered


def test_a_non_finite_timestamp_in_a_recording_is_invalid_input_in_run_too():
    recorded = _auto_energy().run(FRAMES[:3], timestamps=[0.0, float("inf"), 2.0])
    assert [int(status) for status in recorded.status] == [0, 3, 0]
