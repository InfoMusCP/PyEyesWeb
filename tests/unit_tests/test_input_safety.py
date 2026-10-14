"""Wrong arguments must raise or report, never crash the interpreter or return inf / NaN as OK."""

import numpy as np
import pytest

from pyeyesweb.data_models import Status
from pyeyesweb.low_level import Kinematics, KineticEnergy
from pyeyesweb.mid_level import average_curvature_3d
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


# ------------------------------------------------------------- timestamps that are not finite
@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -float("inf")])
@pytest.mark.parametrize("make, data", [(_auto_kinematics, FRAMES[0, 0, :]), (_auto_energy, FRAMES[0])])
def test_a_non_finite_or_huge_timestamp_raises_value_error(make, data, bad):
    with pytest.raises(ValueError):
        make().process(data, timestamp=bad)
