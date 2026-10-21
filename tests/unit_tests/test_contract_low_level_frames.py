"""The call contract (docs/user_guide/input_contract.md) for the low-level frame features: contraction, symmetry,
equilibrium, direction change and the EyesWeb CurvatureVelocityCorrelation. Needs the compiled core (EYESWEB_CORE_PATH)."""
import math
import os
import sys
from pathlib import Path

import numpy as np
import pytest

if os.environ.get("EYESWEB_CORE_PATH"):
    sys.path.insert(0, os.environ["EYESWEB_CORE_PATH"])
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

pytest.importorskip("pyeyesweb._core", exc_type=ImportError)

from contract_suite import check_feature_contract  # noqa: E402
from symmetry_inputs import reflection  # noqa: E402
from floats import assert_same_floats  # noqa: E402
from pyeyesweb.data_models import InputKind, Status  # noqa: E402
from pyeyesweb.low_level import (  # noqa: E402
    BoundingBoxFilledArea, DirectionChange, Equilibrium, EllipsoidSphericity, PointsDensity, CurvatureVelocityCorrelation, Symmetry,
    TriangleSymmetry
)

RNG = np.random.default_rng(5)
CLOUDS = RNG.standard_normal((30, 8, 3))          # (T, N, 3)
SKELETONS = RNG.standard_normal((30, 3, 3))
LABELS = ["torso", "left_hip", "right_hip"]
RATIO = dict(pairs=[("left_hip", "right_hip")], reference_point="torso")  # the default input type is custom
WALK = np.cumsum(RNG.standard_normal((60, 2, 3)), axis=0)   # (T, signals, dims)
SERIES = np.cumsum(RNG.standard_normal((120, 2)), axis=0)   # (T, channels)


def _same(left, right):
    np.testing.assert_array_equal(left.to_array(), right.to_array())
    assert left.status == right.status


# ------------------------------------------------------------------ contraction

def test_bounding_box_filled_area_contract():
    check_feature_contract(BoundingBoxFilledArea, CLOUDS)
    feature = BoundingBoxFilledArea()
    assert feature.inputs[0].kind is InputKind.POINTS and feature.inputs[0].shape == (None, 3)
    assert feature.process(np.empty((0, 3))).status == Status.INVALID_INPUT
    assert feature.process(CLOUDS[0], timestamp=1.5).timestamp == 1.5


def test_points_density_contract_and_input_forms():
    check_feature_contract(lambda: PointsDensity(labels=list("abcdefgh")), CLOUDS)
    check_feature_contract(lambda: PointsDensity(output_dims="components"), CLOUDS)
    labelled = PointsDensity(labels=list("abcdefgh"))
    assert labelled.inputs[0].labels == tuple("abcdefgh") and labelled.inputs[0].shape == (8, 3)
    as_dict = dict(zip("abcdefgh", map(tuple, CLOUDS[0])))
    _same(labelled.process(CLOUDS[0]), labelled.process(as_dict))
    _same(labelled.process(CLOUDS[0]), PointsDensity().process(CLOUDS[0]))  # labels do not enter the maths
    assert PointsDensity().process({}).status == Status.INVALID_INPUT
    with pytest.raises(ValueError):
        labelled.process(CLOUDS[0][:5])


def test_ellipsoid_sphericity_cloud_and_axes_entry_points():
    check_feature_contract(EllipsoidSphericity, CLOUDS)
    feature = EllipsoidSphericity()
    fit = feature.process(CLOUDS[0])
    assert fit.valid["axis_ratio"] and fit["radii"].shape == (3,)
    axes = feature.process_axes(1.0, 2.0, 3.0, timestamp=0.25)
    assert axes.timestamp == 0.25 and axes.valid["sphericity"] and not axes.valid["radii"]
    assert fit["sphericity"] == pytest.approx(feature.process_axes(*fit["radii"])["sphericity"])


# ------------------------------------------------------------------ symmetry

def test_geometric_symmetry_contract():
    check_feature_contract(lambda: reflection(8, [(0, 1), (2, 3)], 4), CLOUDS)
    with pytest.raises(ValueError, match="skeleton"):  # the joint names fix the number of rows
        reflection(8, [(0, 1)]).process(CLOUDS[0][:1])


@pytest.mark.parametrize("output_dims", ["global", "components"])
def test_symmetry_index_3d_contract_and_input_forms(output_dims):
    check_feature_contract(lambda: Symmetry(**RATIO, labels=LABELS, output_dims=output_dims), SKELETONS)
    feature = Symmetry(**RATIO, labels=LABELS, output_dims=output_dims)
    assert feature.inputs[0].labels == tuple(LABELS) and feature.inputs[0].shape == (3, 3)
    as_dict = dict(zip(LABELS, map(tuple, SKELETONS[0])))
    _same(feature.process(SKELETONS[0]), feature.process(as_dict))
    _same(Symmetry(output_dims=output_dims, **RATIO).process(as_dict), feature.process(as_dict))


def test_symmetry_index_3d_array_needs_labels():
    with pytest.raises(ValueError, match="labels"):
        Symmetry(**RATIO).process(SKELETONS[0])


def test_triangle_symmetry_takes_three_vertices():
    upper, left, right = (RNG.standard_normal((20, 2)) for _ in range(3))
    check_feature_contract(TriangleSymmetry, upper, left, right)
    feature = TriangleSymmetry()
    assert feature.inputs.names == ("upper", "left", "right")
    assert feature.process((0, 1), (-1, 0), (1, 0))["symmetry"] == pytest.approx(1.0)


# ------------------------------------------------------------------ equilibrium

def test_equilibrium_contract():
    check_feature_contract(Equilibrium, CLOUDS[:, 0, :2] * 100, CLOUDS[:, 1, :2] * 100, CLOUDS[:, 2, :2] * 100)
    assert Equilibrium().process(np.zeros(2), np.zeros(2), np.zeros(2)).status == Status.INVALID_INPUT  # the feet coincide


# ------------------------------------------------------------------ direction change

def test_direction_change_contract_and_window():
    check_feature_contract(lambda: DirectionChange(window=10, hop=3), WALK[:, 0, :])
    check_feature_contract(lambda: DirectionChange(window=10, metrics=["cosine"]), WALK[:, 0, :2])  # points
    feature = DirectionChange(window=10, hop=5)
    assert feature.inputs[0].shape == (None,)
    recorded = feature.run(WALK[:, 0, :])
    statuses = list(recorded.status)
    assert statuses[:9] == [int(Status.WARMING_UP)] * 9 and statuses[9] == int(Status.OK)
    assert statuses[10] == int(Status.NO_OUTPUT)


def test_direction_change_process_window_matches_the_streamed_window():
    feature = DirectionChange(window=12, hop=12)
    streamed = feature.run(WALK[:12, 0, :])
    series = WALK[:12, 0, :].T                    # (dims, window)
    direct = feature._process_window(series)
    assert direct.ok and direct["cosine"] == streamed["cosine"][-1] and direct["polygon"] == streamed["polygon"][-1]
    assert feature._process_window(series[:, :2]).status == Status.WARMING_UP


def test_direction_change_selective_schema_and_validation():
    assert DirectionChange(window=5, metrics=["polygon"]).outputs.names == ("polygon",)
    with pytest.raises(ValueError):
        DirectionChange(window=2)


# ------------------------------------------------------------------ smoothness

def test_curvature_velocity_smoothness_contract_and_window():
    check_feature_contract(lambda: CurvatureVelocityCorrelation(window=40, sampling_rate=25.0), SERIES)
    check_feature_contract(lambda: CurvatureVelocityCorrelation(window=40, hop=20, sampling_rate=50.0), SERIES)
    check_feature_contract(lambda: CurvatureVelocityCorrelation(window=40, sampling_rate=25.0), SERIES[:, 0])
    feature = CurvatureVelocityCorrelation(window=40, hop=20, sampling_rate=25.0)
    assert feature.inputs[0].kind is InputKind.SAMPLE
    statuses = list(feature.run(SERIES).status)
    assert statuses[:39] == [int(Status.WARMING_UP)] * 39 and statuses[39] == int(Status.WARMING_UP)
    assert statuses[40] == int(Status.NO_OUTPUT) and statuses[59] == int(Status.OK)


@pytest.mark.parametrize("differentiate", [False, True])
def test_curvature_velocity_velocity_is_per_second_in_both_modes(differentiate):
    t = np.arange(300) / 100.0
    ellipse = np.c_[2 * np.cos(np.pi * t), np.sin(np.pi * t)]
    result = CurvatureVelocityCorrelation(window=100, hop=100, sampling_rate=100.0, differentiate=differentiate).run(ellipse)
    speed = np.pi * np.hypot(2 * np.sin(np.pi * t[200:]), np.cos(np.pi * t[200:]))  # the exact speed, length per second
    assert np.allclose(result.velocity[-1][15:-10], speed[10:-15], rtol=1e-2)  # the filter delays the series by 5 samples
    assert result.velocity_std[-1] == pytest.approx(np.std(result.velocity[-1], ddof=1))
    assert result.smoothness[-1] == pytest.approx(-0.9433871886796, abs=1e-9)
    assert result.curvature_std[-1] == pytest.approx(0.57434934336, abs=1e-9)


def test_curvature_velocity_smoothness_process_window_matches_the_streamed_first_window():
    streamed = CurvatureVelocityCorrelation(window=40, sampling_rate=25.0).run(SERIES[:40])
    direct = CurvatureVelocityCorrelation(window=40, sampling_rate=25.0)._process_window(SERIES[:40].T, timestamp=0.5)
    assert direct.timestamp == 0.5
    for name in ("smoothness", "curvature", "velocity", "curvature_std", "velocity_std"):
        np.testing.assert_array_equal(direct[name], streamed[name][-1])


def test_curvature_velocity_smoothness_reset_restores_the_filter_history():
    feature = CurvatureVelocityCorrelation(window=40, hop=20, sampling_rate=25.0)
    first = feature.run(SERIES)
    again = feature.run(SERIES)
    np.testing.assert_array_equal(first["smoothness"], again["smoothness"])


def test_curvature_velocity_smoothness_time_is_seconds_of_the_newest_sample():
    ts = np.arange(len(SERIES)) * 0.02
    timed = CurvatureVelocityCorrelation(window=40, hop=20, sampling_rate=25.0).run(SERIES, timestamps=ts)
    assert timed.timestamps[39] == pytest.approx(ts[39])
    assert math.isnan(CurvatureVelocityCorrelation(window=40, sampling_rate=25.0).run(SERIES).timestamps[39])


def test_triangle_symmetry_is_one_minus_the_frozen_asymmetry():
    """`symmetry` equals `1.0 - asymmetry` bit for bit, the asymmetry being what the feature output before (frozen)."""
    reference = np.load(Path(__file__).resolve().parents[1] / "data" / "triangle_asymmetry_reference.npz")
    rng = np.random.default_rng(21)
    cases = [tuple(rng.normal(size=(3, 2)) * 50) for _ in range(3000)][:300] + [
        ((0, 10), (-5, 0), (5, 0)), ((0, 0), (1, 1), (2, 2)), ((0, 0), (0, 0), (0, 0)), ((0, 0), (1, 0), (2, 0)), ((0, 1), (-1, 0), (1, 0)),
        ((0, 1), (-1, 0), (1, 1)), ((0, 1), (-1, 5), (1, 5)), ((0, 0), (1, 1), (3, 5)), ((0, 0), (-2, 3), (1, 1)),
        ((np.nan, 0), (1, 1), (2, 2)), ((np.inf, 0), (1, 1), (-2, 2)), ((), (1, 1), (2, 2)), ((0, 0), (1, 1), (-1, 1)),
        ((0.1, 0.2), (-0.3, 0.7), (0.9, 0.7)), ((3, 3), (3, 4), (3, 5))]
    feature = TriangleSymmetry()
    for index, case in enumerate(cases):
        result = feature.process(*case)
        assert result.status.name == reference["status"][index]
        # the central finite check says it before the feature: NaN or infinity is not "empty vertex or NaN / infinite coordinates"
        assert result.reason in (reference["reason"][index], "NaN or infinite values")
        expected = np.float64(np.nan) if result.status is Status.INVALID_INPUT else 1.0 - np.float64(reference["asymmetry"][index])
        assert_same_floats(result.symmetry, expected)  # no number when invalid; platform rounding of the frozen file tolerated
