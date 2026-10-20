"""`Kinematics` with several `output_type`s, and the classmethod constructors of the input modes.

Each output of one multi-output instance must be bit-identical to the single-output instance of that type: Qualisys
trials and synthetic signals, 1 to 3 dimensions, point and time-series input, timestamps and `sampling_rate`.
Needs the compiled core (EYESWEB_CORE_PATH).
"""

import numpy as np
import pytest

pytest.importorskip("pyeyesweb._core")

from pyeyesweb.data_models import Status  # noqa: E402
from pyeyesweb.datasets import load_qualisys_trial  # noqa: E402
from pyeyesweb.low_level import Kinematics, KineticEnergy, LogDimensionlessJerk  # noqa: E402

TYPES = ["curvature", "velocity", "direction", "acceleration", "jerk", "smoothed"]
FILTER = dict(filter_window_length=9, filter_polyorder=3)
RNG = np.random.default_rng(5)


def _qualisys(trial, joints=("Right_Hand", "Head", "Left_Foot")):
    """Positions (T, 3 * len(joints)) in metres of some joints of a Qualisys trial, or None without the data."""
    try:
        recording = load_qualisys_trial(trial)
    except FileNotFoundError:  # no copy of the recordings (sdist, or a clone without examples/data)
        return None
    return np.concatenate([recording.joint(joint)[:300] for joint in joints], axis=1) / 1000.0


SIGNALS = {
    "synthetic": np.cumsum(RNG.normal(size=(120, 9)), axis=0) * 0.01,
    "sine": np.stack([np.sin(np.arange(120) / 7.0 + phase) for phase in range(9)], axis=1),
    "still": np.ones((60, 9)),  # direction of a still point is NaN: the bits must agree too
    "qualisys 7": _qualisys(7),
    "qualisys 11": _qualisys(11),
}
SIGNALS = {name: signal for name, signal in SIGNALS.items() if signal is not None}
TIMES = {"timestamps": "timestamps", "sampling_rate": "sampling_rate", "per sample": None}


def _bits(value):
    return np.asarray(value, dtype=float).tobytes()


def _time(kind, count):
    """`(parameters, timestamps)` of the time rule `kind`: irregular timestamps, a sampling rate, or per-sample."""
    if kind == "timestamps":
        return {}, np.cumsum(RNG.uniform(0.008, 0.012, size=count)) + 0.5
    return ({"sampling_rate": 100.0} if kind == "sampling_rate" else {}), [None] * count


def _frames(mode, dims, series):
    """The calls of `mode`: each sample of the first `dims` columns, or growing `(dims, N)` windows of it."""
    data = series[:, :dims]
    if mode == "point":
        return list(data)
    length = FILTER["filter_window_length"]  # the shortest series the block accepts
    return [data[start:start + length].T for start in range(len(data) - length)]


@pytest.mark.parametrize("signal", SIGNALS)
@pytest.mark.parametrize("dims", [1, 2, 3])
@pytest.mark.parametrize("mode", ["point", "time_series"])
@pytest.mark.parametrize("time", TIMES)
@pytest.mark.parametrize("output_dims", ["tangential", "components"])
def test_each_output_of_several_equals_the_single_output_instance(signal, dims, mode, time, output_dims):
    frames = _frames(mode, dims, SIGNALS[signal])
    parameters, stamps = _time(time, len(frames))
    common = dict(dims=dims, input_mode=mode, output_dims=output_dims, **FILTER, **parameters)
    many = Kinematics(output_type=TYPES, **common)
    singles = {kind: Kinematics(output_type=kind, **common) for kind in TYPES}
    assert many.outputs.names == tuple(TYPES)
    for frame, stamp in zip(frames, stamps):
        result = many.process(frame, timestamp=stamp)
        expected = {kind: single.process(frame, timestamp=stamp) for kind, single in singles.items()}
        for kind in TYPES:
            if result.status is Status.OK:  # an invalid result carries no numbers
                assert _bits(result[kind]) == _bits(expected[kind][kind]), kind
            assert (np.shape(result[kind]) == (dims,)) == (kind == "direction" or output_dims == "components")
        assert result.timestamp == pytest.approx(expected["velocity"].timestamp, nan_ok=True)
        # one status for the whole result: not finite when any single-output instance says so
        assert (result.status is Status.INVALID_INPUT) == any(each.status is Status.INVALID_INPUT for each in expected.values())


@pytest.mark.parametrize("dims", [1, 3])
def test_run_of_several_outputs_equals_the_singles(dims):
    data = SIGNALS["qualisys 7"][:, :dims]
    many = Kinematics(dims=dims, output_type=["velocity", "acceleration"], output_dims="components", sampling_rate=100.0, **FILTER).run(data)
    for kind in ("velocity", "acceleration"):
        single = Kinematics(dims=dims, output_type=kind, output_dims="components", sampling_rate=100.0, **FILTER).run(data)
        assert _bits(many[kind]) == _bits(single[kind])


def test_the_dimension_is_inferred_for_several_outputs():
    feature = Kinematics(output_type=["velocity", "jerk"], output_dims="components", **FILTER)
    result = feature.process(SIGNALS["synthetic"][0, :2])
    assert feature.outputs["velocity"].shape == (2,) and result.velocity.shape == (2,) and result.jerk.shape == (2,)


def test_direction_is_a_vector_next_to_tangential_outputs():
    feature = Kinematics(dims=2, output_type=["velocity", "direction"], output_dims="tangential", **FILTER)
    assert feature.outputs["velocity"].shape == () and feature.outputs["direction"].shape == (2,)


def test_the_order_of_the_outputs_is_the_requested_one():
    assert Kinematics(dims=2, output_type=["jerk", "velocity"]).outputs.names == ("jerk", "velocity")
    assert Kinematics(dims=2, output_type="jerk").outputs.names == ("jerk",)


def test_a_non_finite_input_is_invalid_for_every_output():
    feature = Kinematics(dims=2, output_type=["velocity", "acceleration"], **FILTER)
    result = feature.process([np.nan, 1.0])
    assert result.status is Status.INVALID_INPUT and not any(result.valid.values())


# ------------------------------------------------------------------------------------------------ the factories
def test_kinetic_energy_factories_pick_the_input_mode():
    positions = RNG.normal(size=(30, 25, 3))
    velocities = np.diff(positions, axis=0)
    from_position = KineticEnergy.from_position(skeleton="kinect_v2")
    from_velocity = KineticEnergy.from_velocity(skeleton="kinect_v2")
    assert (from_position.input_mode, from_velocity.input_mode) == ("position", "velocity")
    assert from_position.run(positions)["kinetic_energy"][0] == 0.0  # stateful: the first frame has no previous one
    assert from_velocity.run(velocities)["kinetic_energy"][0] > 0.0  # stateless: energy from the first frame on
    assert np.allclose(from_velocity.run(velocities)["kinetic_energy"], from_position.run(positions)["kinetic_energy"][1:])


def test_kinematics_factories_pick_the_input_mode():
    point, series = Kinematics.from_point(dims=2, **FILTER), Kinematics.from_series(dims=2, **FILTER)
    assert (point.input_mode, series.input_mode) == ("point", "time_series")
    assert point.inputs.names == ("point",) and series.inputs.names == ("series",)
    assert Kinematics.from_point(output_type=["velocity", "acceleration"], output_dims="components").outputs.names == ("velocity", "acceleration")


def test_log_dimensionless_jerk_factories_and_the_renamed_parameter():
    profile = np.abs(np.sin(np.linspace(0, 3, 60))) * 40
    velocity = LogDimensionlessJerk.from_velocity(window=60, sampling_rate=100.0)
    acceleration = LogDimensionlessJerk.from_acceleration(window=60, sampling_rate=100.0)
    assert (velocity.input_mode, acceleration.input_mode) == ("velocity", "acceleration")
    assert acceleration._process_window(profile).log_dimensionless_jerk == \
        LogDimensionlessJerk(input_mode="acceleration", window=60, sampling_rate=100.0)._process_window(profile).log_dimensionless_jerk
    with pytest.raises(TypeError, match="'signal'.*input_mode"):
        LogDimensionlessJerk(signal="acceleration", sampling_rate=50.0)


@pytest.mark.parametrize("window", [5, 9, 15])
def test_the_estimate_lags_the_newest_sample_by_half_a_window(window):
    """The fit uses the newest `filter_window_length` samples, newest included, and reads their centre (2026-10-14)."""
    ramp = np.arange(40.0)
    feature = Kinematics(dims=1, filter_window_length=window, output_type="smoothed")
    smoothed = [float(feature.process([value]).smoothed) for value in ramp]
    assert smoothed[-1] == pytest.approx(ramp[-1] - (window - 1) // 2)
    series = Kinematics.from_series(dims=1, filter_window_length=window, output_type="smoothed")
    assert float(series.process(ramp[None, -window:]).smoothed) == pytest.approx(ramp[-1] - (window - 1) // 2)


def test_a_series_needs_filter_window_length_samples():
    series = Kinematics.from_series(dims=1, filter_window_length=7)
    with pytest.raises(ValueError):
        series.process(np.zeros((1, 6)))
    assert series.process(np.zeros((1, 7))).status is Status.OK
