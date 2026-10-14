"""Directness, TrajectoryNonPlanarity and Kinematics (point and time-series input) against a frozen reference.

The reference file `tests/data/trajectory_reference.npz` holds the outputs these features gave while they ran on the
removed Trajectory datatype; the plain-array implementations must reproduce them bit for bit (NaN equal).
Regenerate with `python tools/regenerate_trajectory_reference.py` ONLY when a numeric change is intended.
Needs the compiled core (EYESWEB_CORE_PATH).
"""

import json
from pathlib import Path

import numpy as np
import pytest

REFERENCE = Path(__file__).resolve().parents[1] / "data" / "trajectory_reference.npz"

pytest.importorskip("pyeyesweb._core", exc_type=ImportError)

from pyeyesweb.low_level import Kinematics  # noqa: E402
from pyeyesweb.low_level import Directness, TrajectoryNonPlanarity  # noqa: E402


def _walk(count, dims, seed):
    return np.cumsum(np.random.default_rng(seed).normal(size=(count, dims)), axis=0)[::-1].copy()  # row 0 = newest


def _point_sets():
    angles = np.linspace(0, 4 * np.pi, 40)
    sets = {}
    for dims in (2, 3):
        sets[f"empty{dims}"] = np.zeros((0, dims))
        sets[f"one{dims}"] = np.ones((1, dims))
        sets[f"two{dims}"] = np.array([[1.0] * dims, [0.0] * dims])
        sets[f"zero_length{dims}"] = np.full((6, dims), 2.5)
        sets[f"short{dims}"] = _walk(4, dims, 1)
        sets[f"medium{dims}"] = _walk(40, dims, 2)
        sets[f"long{dims}"] = _walk(300, dims, 3)
        nan = _walk(10, dims, 4)
        nan[3, 0] = np.nan
        sets[f"nan{dims}"] = nan
        infinite = _walk(10, dims, 5)
        infinite[5, -1] = np.inf
        sets[f"inf{dims}"] = infinite
    line = np.zeros((20, 3))
    line[:, 0] = np.arange(20.0)[::-1]
    sets["line3"] = line
    sets["circle3"] = np.stack([np.cos(angles), np.sin(angles), np.zeros_like(angles)], axis=1)
    sets["helix3"] = np.stack([np.cos(angles), np.sin(angles), angles / 5], axis=1)
    sets["duplicates3"] = np.repeat(_walk(8, 3, 6), 3, axis=0)
    return sets


def _outcome(feature, data, timestamp=None):
    try:
        result = feature.process(data, timestamp=timestamp)
    except Exception as error:  # noqa: BLE001
        return ["raises " + type(error).__name__, "", []]
    values = [np.asarray(result[name], dtype=float).ravel() for name in feature.outputs.names]
    return [result.status.name, result.reason, np.concatenate(values).tolist() if values else []]


def _static_cases():
    cases = {}
    points = _point_sets()
    for name, data in points.items():
        cases[f"directness/{name}"] = ("Directness", {}, [data])
        for parameters in ({}, {"radius": 0.1}, {"radius": 2.0, "nan_fraction": 0.0}, {"nan_fraction": 1.0, "nan_value": -1.0},
                           {"output_type": "curvature_value", "radius": 5.0}, {"radius": 0.3, "units": "mm"}):
            cases[f"curvature/{name}/{json.dumps(parameters, sort_keys=True)}"] = ("TrajectoryNonPlanarity", parameters, [data])
    return cases


def _kinematics_cases():
    cases = {}
    for dims in (1, 2, 3):
        rng = np.random.default_rng(10 + dims)
        samples = np.cumsum(rng.normal(size=(24, dims)), axis=0)
        bad = samples.copy()
        bad[20, 0] = np.nan
        stamps = np.cumsum(0.01 + 0.002 * rng.random(24))
        for mode in ("point", "time_series"):
            for output_type in ("smoothed", "velocity", "acceleration", "jerk", "curvature", "direction"):
                for output_dims in ("tangential", "components"):
                    cases[f"kinematics/{mode}/{dims}/{output_type}/{output_dims}"] = (
                        "Kinematics", dict(dims=dims, input_mode=mode, output_type=output_type, output_dims=output_dims),
                        samples, stamps)
        for mode in ("point", "time_series"):
            cases[f"kinematics/{mode}/{dims}/nan"] = ("Kinematics", dict(dims=dims, input_mode=mode), bad, stamps)
            cases[f"kinematics/{mode}/{dims}/small_window"] = (
                "Kinematics", dict(dims=dims, input_mode=mode, filter_window_length=7, filter_polyorder=2, output_type="curvature",
                                   movement_threshold=0.001), samples, None)
    return cases


def _kinematics_outcomes(args):
    _, parameters, samples, stamps = args
    feature = Kinematics(**parameters)
    window = parameters.get("filter_window_length", 15)  # the shortest series the block accepts
    out = []
    if parameters["input_mode"] == "point":
        for index, sample in enumerate(samples):
            out.append(_outcome(feature, sample, None if stamps is None else float(stamps[index])))
    else:
        for index in range(window, len(samples) + 1):
            out.append(_outcome(feature, samples[index - window:index].T, None if stamps is None else float(stamps[index - 1])))
    return out


def compute():
    """name -> list of [status, reason, values] for every case."""
    outcomes = {}
    for name, (kind, parameters, arrays) in _static_cases().items():
        feature = Directness(**parameters) if kind == "Directness" else TrajectoryNonPlanarity(**parameters)
        outcomes[name] = [_outcome(feature, arrays[0])]
    for name, args in _kinematics_cases().items():
        outcomes[name] = _kinematics_outcomes(args)
    return outcomes


def _pack(outcomes):
    """(all values in one array, {case: [[status, reason, count], ...]})."""
    meta = {name: [[call[0], call[1], len(call[2])] for call in calls] for name, calls in outcomes.items()}
    values = np.array([value for calls in outcomes.values() for call in calls for value in call[2]], dtype=float)
    return values, meta


def _bits(values):
    values = np.asarray(values, dtype=float).copy()
    values[np.isnan(values)] = 0.123456789  # every NaN equal
    return values.view(np.uint64)


def test_outputs_match_the_frozen_reference_bit_for_bit():
    values, meta = _pack(compute())
    with np.load(REFERENCE) as data:
        frozen_meta = json.loads(str(data["meta"]))
        frozen = data["values"]
    assert meta == frozen_meta  # same cases, statuses, reasons and value counts
    assert values.shape == frozen.shape
    different = np.flatnonzero(_bits(values) != _bits(frozen))
    assert not different.size, f"{different.size} values differ, first at {different[:10]}: {values[different[:3]]} vs {frozen[different[:3]]}"

