"""One way to express time (timestamps, else `sampling_rate`, else per sample) and one unit convention (`units`)."""

import inspect

import numpy as np
import pytest

pytest.importorskip("pyeyesweb._core")

from pyeyesweb.low_level import CurvatureDispersion, Equilibrium, Kinematics, KineticEnergy
from pyeyesweb.low_level import MotionNoiseDetector, TrajectoryNonPlanarity
from pyeyesweb.mid_level import GestureSegmenter
from pyeyesweb.physical_signals import HitCellDetector

LABELS = ["a"]
LINE = np.arange(12.0).reshape(12, 1, 1) * np.array([1.0, 0.0, 0.0])  # one joint moving 1 unit per frame along x
NOTE = "per-sample"


def _energy(**params):
    return KineticEnergy(labels=LABELS, weights={"a": 1.0}, **params)


# ------------------------------------------------------------------------------ the rule: t > sampling_rate > none
def test_timestamps_sampling_rate_and_neither_agree_on_the_step():
    with_ts = _energy().run(LINE, timestamps=np.arange(12) * 0.02)["kinetic_energy"]
    with_rate = _energy(sampling_rate=50).run(LINE)["kinetic_energy"]
    per_sample = _energy().run(LINE)["kinetic_energy"]
    assert np.allclose(with_ts[1:], 0.5 * 50 ** 2) and np.allclose(with_rate[1:], 0.5 * 50 ** 2)
    assert np.allclose(per_sample[1:], 0.5)


def test_timestamps_win_over_sampling_rate():
    ke = _energy(sampling_rate=10)
    ke.process(LINE[0], timestamp=1.0)
    assert ke.process(LINE[1], timestamp=1.02).kinetic_energy == pytest.approx(0.5 * 50 ** 2)  # not 10 Hz
    assert NOTE not in ke.process(LINE[2], timestamp=1.04).reason


def test_without_time_the_result_says_so_and_with_a_rate_it_does_not():
    assert NOTE in _energy().process(LINE[0]).reason
    assert NOTE not in _energy(sampling_rate=50).process(LINE[0]).reason
    first = _energy()
    assert NOTE in first.process(LINE[0], timestamp=0.5).reason  # the first timed call has no previous timestamp: per sample
    assert NOTE not in first.process(LINE[1], timestamp=0.52).reason


def test_the_time_source_may_change_between_calls():
    ke = _energy(sampling_rate=100)
    ke.process(LINE[0])
    assert ke.process(LINE[1]).kinetic_energy == pytest.approx(0.5 * 100 ** 2)
    assert ke.process(LINE[2], timestamp=5.0).ok  # switching to a timestamp keeps the state and does not raise


def test_time_mode_is_not_a_parameter():
    for cls in (KineticEnergy, Kinematics, MotionNoiseDetector):
        assert "time_mode" not in inspect.signature(cls).parameters
        assert "sampling_rate" in inspect.signature(cls).parameters
    with pytest.raises(TypeError, match="time_mode"):
        Kinematics(time_mode=0)
    with pytest.raises(AttributeError):
        _energy().time_mode = 0


@pytest.mark.parametrize("make", [lambda rate: _energy(sampling_rate=rate), lambda rate: Kinematics(sampling_rate=rate),
                                  lambda rate: MotionNoiseDetector(labels=LABELS, sampling_rate=rate)])
def test_sampling_rate_accepts_int_and_float(make):
    assert make(100.0).sampling_rate == 100.0 and make(100).sampling_rate == 100


def test_sampling_rate_can_be_changed_live_and_removed():
    ke = _energy(sampling_rate=50)
    ke.process(LINE[0])
    ke.sampling_rate = 100.0
    assert ke.process(LINE[1]).kinetic_energy == pytest.approx(0.5 * 100 ** 2)
    ke.sampling_rate = None
    assert NOTE in ke.process(LINE[2]).reason


# ------------------------------------------------------------------------------------------------- the three traps
POINTS = np.cumsum(np.random.default_rng(1).standard_normal((12, 3)), axis=0)[::-1]  # row 0 = newest


@pytest.mark.parametrize("start", [0.0, 5.0])
def test_a_first_timestamp_of_zero_is_like_any_start_time(start):
    rng = np.random.default_rng(3)
    velocity = np.cumsum(rng.normal(size=(40, 3)), axis=0)
    velocity[0] = 0  # a first speed of 0 adds no arc length at the first step
    acceleration = rng.normal(size=(40, 3))
    smoothness = CurvatureDispersion()
    values = [smoothness.process(*pair, timestamp=start + 0.02 * index).curvature_dispersion
              for index, pair in enumerate(zip(velocity, acceleration))]
    assert np.isfinite(values[1:]).all()
    again = CurvatureDispersion()
    shifted = [again.process(*pair, timestamp=7 + 0.02 * index).curvature_dispersion
               for index, pair in enumerate(zip(velocity, acceleration))]
    assert np.allclose(values[2:], shifted[2:])  # only the first step depends on where time starts


# ----------------------------------------------------------------------------------------------------- units "mm"
def _gesture(scale, units):
    rng = np.random.default_rng(5)
    steps = np.concatenate([rng.normal(0, 1e-4, (20, 3)), rng.normal(0, 0.05, (20, 3)), rng.normal(0, 1e-4, (20, 3))])
    frames = np.cumsum(steps, axis=0).reshape(60, 1, 3) * scale  # metres, or the same motion in millimetres
    energy = KineticEnergy(labels=LABELS, weights={"a": 1.0}, sampling_rate=50.0).run(frames)["kinetic_energy"]
    noise = MotionNoiseDetector(labels=LABELS, noise_threshold=0.5, sampling_rate=50.0, units=units).run(frames)["is_noisy"]
    noise = ~np.asarray(noise, dtype=bool)  # the segmenter blocks a start while its input is set
    squared = 1e6 if units == "mm" else 1.0  # the energy of data in millimetres is in mm^2
    segmented = GestureSegmenter(filter_window_length=5, firing_threshold=0.1 * squared).run(energy, noise)
    return {"kinetic_energy": energy, "noise": noise, **{name: segmented[name] for name in ("is_gesturing", "is_gesture_start", "is_gesture_end")}}


def test_gesture_segmenter_in_millimetres_gives_the_same_segmentation():
    metres, millimetres = _gesture(1.0, "m"), _gesture(1000.0, "mm")
    assert metres["is_gesturing"].any() and not metres["is_gesturing"].all()  # the thresholds matter in this recording
    for name in ("is_gesturing", "is_gesture_start", "is_gesture_end", "noise"):
        assert np.array_equal(metres[name], millimetres[name]), name
    assert np.allclose(millimetres["kinetic_energy"], 1e6 * np.asarray(metres["kinetic_energy"]))  # outputs keep the data unit


def test_without_units_millimetre_data_does_not_segment_like_metres():
    unscaled = _gesture(1000.0, "m")
    assert not np.array_equal(unscaled["is_gesturing"], _gesture(1.0, "m")["is_gesturing"])


def test_kinematics_threshold_in_millimetres():
    times = np.linspace(0, 4 * np.pi, 80)
    helix = np.stack([np.cos(times), np.sin(times), 0.1 * times], axis=1)
    kwargs = dict(output_type="curvature", sampling_rate=50.0, movement_threshold=0.5)
    metres = Kinematics(**kwargs).run(helix)["curvature"]
    millimetres = Kinematics(units="mm", **kwargs).run(helix * 1000.0)["curvature"]
    assert np.allclose(np.asarray(millimetres) * 1000.0, metres, rtol=1e-9, atol=1e-12)  # curvature is 1 / length
    assert (np.asarray(metres) == 0).any() and (np.asarray(metres) > 0).any()  # the threshold decided


def test_hit_cell_area_in_millimetres():
    points = np.array([[0.55, 0.15], [0.05, 0.95]])
    assert np.array_equal(HitCellDetector().process(points).cells,
                          HitCellDetector(units="mm").process(points * 1000).cells)


def test_units_are_validated_shown_and_live():
    assert inspect.signature(MotionNoiseDetector).parameters["units"].default == "m"
    assert "units" not in inspect.signature(GestureSegmenter).parameters  # its threshold is in the unit of its input
    assert "units" not in inspect.signature(KineticEnergy).parameters  # no unit-sensitive parameter
    with pytest.raises(ValueError, match="units"):
        Kinematics(units="km")
    kin = Kinematics(output_type="curvature", movement_threshold=0.5)
    kin.units = "mm"
    assert kin.units == "mm"
    with pytest.raises(ValueError, match="units"):
        kin.units = "inch"


def test_equilibrium_margin_in_millimetres():
    points = np.array([[-0.3, 0.0], [0.3, 0.0], [0.1, 0.05]])
    metres = Equilibrium(margin=0.4).process(*points)
    millimetres = Equilibrium(margin=0.4, units="mm").process(*(points * 1000))
    assert 0 < metres.equilibrium < 1
    assert millimetres.equilibrium == pytest.approx(metres.equilibrium) and millimetres.angle == pytest.approx(metres.angle)


def test_average_curvature_radius_in_millimetres():
    points = np.random.default_rng(4).normal(size=(60, 3)) * 0.2
    metres = TrajectoryNonPlanarity(radius=0.3).process(points)
    millimetres = TrajectoryNonPlanarity(radius=0.3, units="mm").process(points * 1000)
    assert millimetres.curvature_radius == pytest.approx(1000 * metres.curvature_radius)
    assert TrajectoryNonPlanarity(radius=0.3).process(points * 1000).curvature_radius != metres.curvature_radius
