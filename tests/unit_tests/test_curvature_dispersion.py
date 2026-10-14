"""CurvatureDispersion: the curvature-based smoothness index fed with the velocity and acceleration of `Kinematics`.

Needs the compiled core (EYESWEB_CORE_PATH). The reference file `tests/data/curvature_dispersion_reference.npz` holds
inputs (synthetic paths and windows of Qualisys trials) and the outputs of the composition (the dispersion fed with the
velocity and acceleration components of two `Kinematics`), which the composition must reproduce bit for bit. It was first
cut from the former `Kinematics(output_type="smoothness")`; on 2026-10-14 `Kinematics` began to use the newest samples
(one sample less lag), so the expected outputs were regenerated from the new `Kinematics` (the inputs and parameters are
unchanged). Regenerate (expected = `_composition`) ONLY when a numeric change is intended.
"""

import inspect
import json
import math
from pathlib import Path

import numpy as np
import pytest

from contract_suite import check_feature_contract
from live_param_suite import NOTE, check_invalid, check_live, check_structural, feed, ids

from pyeyesweb.catalog import catalog
from pyeyesweb.data_models import Status
from pyeyesweb.low_level import CurvatureDispersion, Kinematics

REFERENCE = Path(__file__).resolve().parents[1] / "data" / "curvature_dispersion_reference.npz"
_rng = np.random.default_rng(21)
STEPS = np.cumsum(_rng.normal(size=(80, 3)), axis=0)
VELOCITY = np.gradient(STEPS, axis=0)
ACCELERATION = np.gradient(VELOCITY, axis=0)


def _composition(points, params, timestamps):
    """The new way to the old output: two Kinematics (components) into CurvatureDispersion, one call per sample."""
    params = dict(params)
    length = params.pop("standard_deviation_length")
    dims = points.shape[1]
    own = {key: params.pop(key) for key in ("movement_threshold",) if key in params}
    smoothness = CurvatureDispersion(dims=dims, window=length, **own,
                                     **{key: value for key, value in params.items() if key in ("sampling_rate", "units")})
    velocity, acceleration = (Kinematics(dims=dims, output_type=kind, output_dims="components", **params)
                              for kind in ("velocity", "acceleration"))
    values = []
    for index, point in enumerate(points):
        stamp = None if timestamps is None else float(timestamps[index])
        values.append(smoothness.process(velocity.process(point, timestamp=stamp).velocity,
                                         acceleration.process(point, timestamp=stamp).acceleration,
                                         timestamp=stamp).curvature_dispersion)
    return np.array(values)


def _reference_cases():
    with np.load(REFERENCE) as data:
        parameters = json.loads(str(data["parameters"]))
        return [(name, data[f"{name}/points"], data[f"{name}/timestamps"] if f"{name}/timestamps" in data else None,
                 data[f"{name}/expected"], params) for name, params in parameters.items()]


@pytest.mark.parametrize("name, points, timestamps, expected, params", _reference_cases(),
                         ids=lambda value: value if isinstance(value, str) else "")
def test_composition_reproduces_the_frozen_output_exactly(name, points, timestamps, expected, params):
    actual = _composition(points, params, timestamps)
    assert actual.shape == expected.shape
    assert np.array_equal(actual.view(np.int64)[~np.isnan(actual)], expected.view(np.int64)[~np.isnan(expected)])
    assert np.array_equal(np.isnan(actual), np.isnan(expected))


# -------------------------------------------------------------------------------------------------------- contract

@pytest.mark.parametrize("build", [lambda: CurvatureDispersion(window=10, sampling_rate=50.0),
                                   lambda: CurvatureDispersion(dims=3, window=10), lambda: CurvatureDispersion(),
                                   lambda: CurvatureDispersion(dims=2, window=5, units="mm")])
def test_contract(build):
    dims = build().dims or 3
    check_feature_contract(build, VELOCITY[:, :dims], ACCELERATION[:, :dims])


def test_declared_inputs_and_outputs():
    feature = CurvatureDispersion(dims=2)
    assert feature.inputs.names == ("velocity", "acceleration")
    assert all(declared.shape == (2,) for declared in feature.inputs)
    assert feature.outputs.names == ("curvature_dispersion",)
    assert CurvatureDispersion().inputs[0].shape == (None,)


def test_the_catalog_lists_it_as_a_low_level_feature():
    entry = next(feature for feature in catalog() if feature.name == "CurvatureDispersion")
    assert entry.layer.name == "LOW_LEVEL"


def test_signature_and_defaults():
    parameters = inspect.signature(CurvatureDispersion).parameters
    assert list(parameters) == ["dims", "window", "movement_threshold", "sampling_rate", "units"]
    assert parameters["window"].default == 50 and parameters["movement_threshold"].default == 0.005
    with pytest.raises(TypeError, match="window"):
        CurvatureDispersion(windows=10)


# ----------------------------------------------------------------------------------------------------- behaviour

def test_it_outputs_from_the_first_call_and_is_one_below_the_movement_threshold():
    feature = CurvatureDispersion(window=4)
    first = feature.process(VELOCITY[0], ACCELERATION[0])
    assert first.status is Status.OK and math.isfinite(first.curvature_dispersion)
    still = CurvatureDispersion(window=4)
    assert still.process([0.001, 0, 0], [0, 1, 0]).curvature_dispersion == 1.0


def test_reset_clears_the_rings():
    feature = CurvatureDispersion(window=6)
    first = [feature.process(velocity, acceleration).curvature_dispersion for velocity, acceleration in zip(VELOCITY[:9], ACCELERATION[:9])]
    feature.reset()
    again = [feature.process(velocity, acceleration).curvature_dispersion for velocity, acceleration in zip(VELOCITY[:9], ACCELERATION[:9])]
    assert first == again


def test_in_one_dimension_the_index_is_nan_above_the_threshold_and_says_so():
    result = CurvatureDispersion(dims=1).process([1.0], [0.5])
    assert result.status is Status.INVALID_INPUT and math.isnan(result.curvature_dispersion) and result.reason


def test_the_time_step_follows_the_library_rule():
    kwargs = dict(window=5)
    stamped = CurvatureDispersion(**kwargs).run(VELOCITY, ACCELERATION, timestamps=np.arange(80) * 0.02 + 1.0)
    rated = CurvatureDispersion(sampling_rate=50, **kwargs).run(VELOCITY, ACCELERATION)
    per_sample = CurvatureDispersion(**kwargs).run(VELOCITY, ACCELERATION)
    assert np.allclose(stamped["curvature_dispersion"][10:], rated["curvature_dispersion"][10:], rtol=1e-9)
    assert not np.allclose(per_sample["curvature_dispersion"], rated["curvature_dispersion"])
    assert "per-sample" in CurvatureDispersion().process(VELOCITY[0], ACCELERATION[0]).reason


def test_units_scale_the_movement_threshold_only():
    in_metres = CurvatureDispersion(window=5, movement_threshold=1.0).process([0.5, 0, 0], [0, 1, 0])
    in_millimetres = CurvatureDispersion(window=5, movement_threshold=0.001, units="mm").process([0.5, 0, 0], [0, 1, 0])
    assert in_metres.curvature_dispersion == in_millimetres.curvature_dispersion == 1.0


# ------------------------------------------------------------------------------------------------------- errors

@pytest.mark.parametrize("velocity, acceleration", [([1.0, 0.0], [0.0, 1.0, 0.0]), ([1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0]),
                                                    (np.ones((3, 3)), np.ones(3)), ([1.0, 0.0, 0.0], 1.0)])
def test_a_wrong_shape_raises_naming_the_input(velocity, acceleration):
    feature = CurvatureDispersion()
    with pytest.raises(ValueError, match="CurvatureDispersion"):
        feature.process(velocity, acceleration)


def test_a_frame_of_another_dimension_than_the_first_raises():
    feature = CurvatureDispersion()
    feature.process([1.0, 0.0], [0.0, 1.0])
    with pytest.raises(ValueError, match="velocity"):
        feature.process([1.0, 0.0, 0.0], [0.0, 1.0, 0.0])
    with pytest.raises(ValueError, match="acceleration"):
        CurvatureDispersion(dims=3).process([1.0, 0.0, 0.0], [0.0, 1.0])


@pytest.mark.parametrize("velocity, acceleration", [([np.nan, 0, 0], [0, 1, 0]), ([1, 0, 0], [0, np.inf, 0])])
def test_non_finite_data_is_invalid_input_and_leaves_the_rings_alone(velocity, acceleration):
    feature, control = CurvatureDispersion(window=4), CurvatureDispersion(window=4)
    bad = feature.process(velocity, acceleration)
    assert bad.status is Status.INVALID_INPUT and bad.reason
    assert feature.process(VELOCITY[0], ACCELERATION[0]) == control.process(VELOCITY[0], ACCELERATION[0])


@pytest.mark.parametrize("params", [dict(dims=4), dict(dims=0), dict(dims=2, window=1), dict(units="km")])
def test_bad_parameters_raise_at_construction(params):
    with pytest.raises(ValueError):
        CurvatureDispersion(**params)


# ------------------------------------------------------------------------------------------ live and structural

# Before the change the speed is below both thresholds, so the rings do not hold the old threshold.
_SLOW = [(np.array([0.001, 0, 0]), np.array([0, 1.0, 0]))] * 60
_MOVING = [(np.array([0.3 + 0.7 * (index % 2), 0, 0]), np.array([0, 1.0, 0])) for index in range(60)]
RECORDING = _SLOW + _MOVING
LIVE = [(lambda: CurvatureDispersion(window=8), "movement_threshold", 0.5, RECORDING)]
STRUCTURAL = [(lambda: CurvatureDispersion(window=8), "window", 12, RECORDING)]
INVALID = [(lambda: CurvatureDispersion(window=8), "window", 1, RECORDING)]


@pytest.mark.parametrize("factory, attr, value, recording", LIVE, ids=ids(LIVE))
def test_live_change_keeps_the_state(factory, attr, value, recording):
    check_live(factory, attr, value, recording)


@pytest.mark.parametrize("factory, attr, value, recording", STRUCTURAL, ids=ids(STRUCTURAL))
def test_structural_change_restarts_and_says_so_once(factory, attr, value, recording):
    check_structural(factory, attr, value, recording)


@pytest.mark.parametrize("factory, attr, value, recording", INVALID, ids=ids(INVALID))
def test_an_invalid_new_value_raises_and_changes_nothing(factory, attr, value, recording):
    check_invalid(factory, attr, value, recording)


def test_a_new_dims_restarts_the_state_and_says_so_once():
    feature = CurvatureDispersion(dims=3, window=8)
    feed(feature, RECORDING[:70])
    feature.dims = 2
    after = feed(feature, [(velocity[:2], acceleration[:2]) for velocity, acceleration in RECORDING[70:]])
    assert NOTE in after[0].reason and all(NOTE not in result.reason for result in after[1:])
    assert feature.inputs[0].shape == (2,)


@pytest.mark.parametrize("attr, value", [("sampling_rate", 100.0), ("units", "mm")])
def test_sampling_rate_and_units_are_live(attr, value):
    feature = CurvatureDispersion(window=8, sampling_rate=50.0)
    feed(feature, RECORDING[:70])
    setattr(feature, attr, value)
    assert all(NOTE not in result.reason for result in feed(feature, RECORDING[70:]))
