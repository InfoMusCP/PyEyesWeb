"""Kinematics input modes, statuses of degenerate data, minimum windows, names and small repetitions of the geometry
family (physical signals, low level, space occupation, directness). Needs the compiled core (EYESWEB_CORE_PATH)."""
import functools
import inspect
import os
import sys
from types import SimpleNamespace

import numpy as np
import pytest

if os.environ.get("EYESWEB_CORE_PATH"):
    sys.path.insert(0, os.environ["EYESWEB_CORE_PATH"])

pytest.importorskip("pyeyesweb._core", exc_type=ImportError)

from symmetry_inputs import reflection  # noqa: E402
from pyeyesweb import physical_signals as ps  # noqa: E402
from pyeyesweb.data_models.inputs import InputKind  # noqa: E402
from pyeyesweb.data_models.results import Status  # noqa: E402
from pyeyesweb.low_level import TrajectoryNonPlanarity  # noqa: E402
from pyeyesweb.low_level import (  # noqa: E402
    DirectionChange, Equilibrium, EllipsoidSphericity, FilterContour, Kinematics, CurvatureVelocityCorrelation, SpectralArcLength,
    LogDimensionlessJerk, Harmonicity, SubmovementCount,
    Symmetry, TriangleSymmetry
)

SPEED_PROFILE_METRICS = tuple(functools.partial(metric, sampling_rate=50.0)  # the rate has no default
                              for metric in (SpectralArcLength, LogDimensionlessJerk, Harmonicity, SubmovementCount))
MODES = SimpleNamespace(POINT="point", TIME_SERIES="time_series")
LINE = np.array([[3.0, 0, 0], [2, 0, 0], [1, 0, 0], [0, 0, 0]])  # row 0 = newest


# ------------------------------------------------------------------------------------------------------ Kinematics

def test_kinematics_inputs_follow_the_input_mode():
    assert Kinematics().inputs["point"].kind is InputKind.SAMPLE
    series = Kinematics(dims=3, input_mode=MODES.TIME_SERIES).inputs["series"]
    assert series.kind is InputKind.MATRIX and series.shape == (3, None)


def test_kinematics_inputs_refresh_when_the_mode_is_set():
    feature = Kinematics(dims=2)
    feature.input_mode = MODES.TIME_SERIES
    assert feature.inputs.names == ("series",) and feature.inputs[0].shape == (2, None)
    feature.input_mode = MODES.POINT
    assert feature.inputs.names == ("point",)


def test_kinematics_has_a_single_entry_point():
    feature = Kinematics()
    assert not hasattr(feature, "_process_window")


def test_kinematics_process_takes_the_shape_of_each_mode():
    assert Kinematics().process([0.0, 0, 0]).ok
    series = np.vstack([np.arange(30.0) ** 2] * 3)
    assert Kinematics(input_mode=MODES.TIME_SERIES).process(series, timestamp=0.5).timestamp == 0.5


def test_kinematics_run_takes_a_recording_of_each_mode():
    series = np.stack([np.vstack([np.arange(30.0) ** 2] * 3) + offset for offset in range(4)])
    assert len(Kinematics(input_mode=MODES.TIME_SERIES).run(series)) == 4
    assert len(Kinematics().run(np.zeros((5, 3)))) == 5


@pytest.mark.parametrize("mode, wrong", [(MODES.POINT, np.zeros(2)), (MODES.TIME_SERIES, np.zeros((2, 30)))])
def test_kinematics_checks_the_shape_in_each_mode(mode, wrong):
    with pytest.raises(ValueError):
        Kinematics(dims=3, input_mode=mode).process(wrong)


def test_kinematics_non_finite_data_is_invalid_input():
    assert Kinematics().process([np.nan, 0, 0]).status is Status.INVALID_INPUT


def test_kinematics_has_no_smoothness_output():
    with pytest.raises(ValueError, match="smoothness"):
        Kinematics(output_type="smoothness")


# --------------------------------------------------------------------------------------------- degenerate data

def test_curvature_velocity_smoothness_first_window_is_warming_up():
    series = np.cumsum(np.random.default_rng(0).standard_normal((120, 2)), axis=0)
    statuses = list(CurvatureVelocityCorrelation(window=40, hop=20, sampling_rate=25.0).run(series).status)
    assert statuses[39] == int(Status.WARMING_UP) and statuses[59] == int(Status.OK)
    first = CurvatureVelocityCorrelation(window=40, sampling_rate=25.0)._process_window(series[:40].T)
    assert first.status is Status.WARMING_UP and first.reason


def test_curvature_velocity_correlation_dynamic_input_recovers_after_a_length_change():
    """A window of another length rebuilds the filters with an empty history: that window is WARMING_UP, the next ones are OK."""
    series = np.cumsum(np.random.default_rng(3).normal(size=(900, 3)), axis=0)
    feature = CurvatureVelocityCorrelation(window=100, input_kind="dynamic", sampling_rate=25.0)
    start, results = 0, []
    for length in (130, 130, 100, 130, 130, 100, 100, 130):
        results.append(feature._process_window(series[start:start + length].T))
        start += length
    warming, ok = Status.WARMING_UP, Status.OK
    assert [result.status for result in results] == [warming, ok, warming, warming, ok, warming, ok, warming]
    assert all(np.isfinite(result.smoothness) for result in results if result.status is ok)
    fresh = CurvatureVelocityCorrelation(window=100, input_kind="dynamic", sampling_rate=25.0)  # started at the window after the change
    fresh._process_window(series[360:490].T)
    assert fresh._process_window(series[490:620].T).smoothness == results[4].smoothness


def test_ellipsoid_sphericity_degenerate_clouds_are_invalid_input():
    feature = EllipsoidSphericity()
    assert feature.process(np.random.default_rng(1).standard_normal((20, 3))).ok
    assert feature.process(np.zeros((1, 3))).status is Status.INVALID_INPUT
    assert feature.process(np.zeros((6, 3))).status is Status.INVALID_INPUT
    for sizes in ((1, 2, 3), (0, 1, 1), (-1, 1, 1)):
        assert feature.process_axes(*sizes).status is (Status.OK if min(sizes) > 0 else Status.INVALID_INPUT)


def test_triangle_symmetry_collinear_vertices_are_invalid_input():
    feature = TriangleSymmetry()
    assert feature.process([0, 0], [-1, 1], [1, 1]).ok
    result = feature.process([0, 0], [1, 1], [2, 2])
    assert result.status is Status.INVALID_INPUT and "collinear" in result.reason
    assert feature.process([0, 0], [np.nan, 1], [1, 1]).status is Status.INVALID_INPUT


def test_average_curvature_with_too_few_points_is_invalid_input():
    feature = TrajectoryNonPlanarity()
    assert feature.process(np.zeros((1, 3))).status is Status.INVALID_INPUT
    assert feature.process(LINE).ok


def test_equilibrium_coincident_feet_are_invalid_input():
    feature = Equilibrium()
    assert feature.process((0.0, 0), (100, 0), (50, 0)).ok
    assert feature.process((0.0, 0), (0, 0), (50, 0)).status is Status.INVALID_INPUT


def test_non_finite_frames_never_raise():
    nan = np.full((3, 3), np.nan)
    assert Equilibrium().process(*nan[:, :2]).status is Status.INVALID_INPUT
    assert reflection(3, [(0, 1)]).process(nan).status is Status.INVALID_INPUT
    for build in SPEED_PROFILE_METRICS:
        assert build()._process_window(np.full(60, np.nan)).status is Status.INVALID_INPUT
    assert DirectionChange(window=3)._process_window(np.full((3, 3), np.inf)).status is Status.INVALID_INPUT


# --------------------------------------------------------------------------------------------- minimum windows

@pytest.mark.parametrize("build, minimum", [(build, 10) for build in SPEED_PROFILE_METRICS] + [(DirectionChange, 3), (functools.partial(CurvatureVelocityCorrelation, sampling_rate=25.0), 10)])
def test_minimum_window_at_construction_and_when_set(build, minimum):
    with pytest.raises(ValueError, match=f">= {minimum}"):
        build(window=minimum - 1)
    feature = build(window=minimum + 5, hop=1)
    with pytest.raises(ValueError, match=f">= {minimum}"):
        feature.window = minimum - 1
    assert feature.window == minimum + 5
    with pytest.raises(ValueError, match=f">= {minimum}"):
        feature.configure(window=minimum - 1)


def test_curvature_velocity_smoothness_minimum_follows_the_filter_window_length():
    assert CurvatureVelocityCorrelation(window=20, filter_window_length=19, sampling_rate=25.0).window == 20
    with pytest.raises(ValueError, match=">= 20"):
        CurvatureVelocityCorrelation(window=19, filter_window_length=19, sampling_rate=25.0)
    feature = CurvatureVelocityCorrelation(window=20, sampling_rate=25.0)
    with pytest.raises(ValueError, match=">= 22"):
        feature.filter_window_length = 21
    feature.filter_window_length = 11
    assert feature.filter_window_length == 11


# ------------------------------------------------------------------------------------------------- kinds, names

def test_direction_change_takes_a_position():
    assert DirectionChange(window=5).inputs[0].kind is InputKind.SAMPLE


@pytest.mark.parametrize("build", [Equilibrium, *SPEED_PROFILE_METRICS, lambda: DirectionChange(window=5),
                                   lambda: CurvatureVelocityCorrelation(window=20, sampling_rate=25.0)])
def test_properties_carry_the_names_of_the_constructor_arguments(build):
    feature = build()
    for name in inspect.signature(type(feature).__init__).parameters:
        if name not in ("self", "params", "kwargs"):
            assert hasattr(feature, name), name


def test_hop_defaults():
    assert all(build().hop == 1 for build in SPEED_PROFILE_METRICS) and DirectionChange(window=5).hop == 1
    assert CurvatureVelocityCorrelation(window=20, sampling_rate=25.0).hop == 1  # hop=window is no overlap (EyesWeb's overlapped_samples = 0)


# ------------------------------------------------------------------------------------------- repetitions removed


def test_quantization_algorithm_is_a_string_not_an_export():
    import pyeyesweb.mid_level as mid
    assert not hasattr(mid, "QuantizationAlgorithm") and not hasattr(ps, "QuantizationAlgorithm")


def test_filter_contour_window_is_a_parameter():
    feature = FilterContour(window=3)
    assert feature.window == 3
    feature.window = 5
    assert feature.window == 5


def test_kinematics_savitzky_golay_parameters():
    parameters = inspect.signature(Kinematics).parameters
    assert parameters["filter_window_length"].default == 15 and parameters["filter_polyorder"].default == 3
    for bad in (dict(filter_window_length=6), dict(filter_window_length=3), dict(filter_window_length=7, filter_polyorder=7)):
        with pytest.raises(ValueError):
            Kinematics(dims=2, **bad)
