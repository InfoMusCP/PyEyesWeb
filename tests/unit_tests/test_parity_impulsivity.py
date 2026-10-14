"""Parity of SuddennessImpulsivity (compiled core) with the preserved pure-Python implementation, which composes
DirectionChange and Suddenness (their preserved references), and of both impulsivity features with the frozen outputs
of `tests/data/impulsivity_reference.npz` (taken before `Impulsivity` became `ContractionImpulsivity`, with its
`threshold` renamed `peak_threshold`, and before SuddennessImpulsivity dropped its intermediate outputs): bit for bit,
statuses and reasons included, on synthetic and Qualisys data, after `reset()` and after live parameter changes.
The `sud_*` data of the frozen file are ONE trajectory `(frames, dims)` (regenerated 2026-10-14 for the one-point-per-frame
decision: marker 0 of the former `(frames, signals, dims)` recordings, marker 1 for the NaN one). Two scenarios were
not regenerated, because their old inputs were one point already: `single_signal` and `still` reproduce the outputs
frozen before the change bit for bit. The statuses of `trial_quantile` (323 frames) and `events` (56 frames) were
regenerated again for #47: the frames whose quantile fit has the alpha = -1 sentinel are INVALID_INPUT (they were OK), the
index values are the same.

Needs the compiled core: found as pyeyesweb._eyesweb_core, or as eyesweb_core in EYESWEB_CORE_PATH; else skipped.
"""
import inspect
import json
import math
import os
import sys
from pathlib import Path

import numpy as np
import pytest

if os.environ.get("EYESWEB_CORE_PATH"):
    sys.path.insert(0, os.environ["EYESWEB_CORE_PATH"])

pytest.importorskip("pyeyesweb._core", exc_type=ImportError)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "reference"))
from impulsivity_reference import SuddennessImpulsivityReference  # noqa: E402
from suddenness_reference import SuddennessReference  # noqa: E402

from pyeyesweb.data_models.results import Status  # noqa: E402
from pyeyesweb.low_level import DirectionChange  # noqa: E402
from pyeyesweb.mid_level import ContractionImpulsivity, Suddenness, SuddennessImpulsivity  # noqa: E402

ALGOS = ["new", "old"]
ENUM = {"new": "constrained", "old": "quantile"}


def _series(window):
    """A `(Time, 1, N_dims)` tensor (the references take a signals axis) as the `(N_dims, Time)` series of the one
    point `_process_window` takes."""
    return np.asarray(window)[:, 0, :].T


def _same(first, second):
    if isinstance(first, float) and math.isnan(first):
        return isinstance(second, float) and math.isnan(second)
    return first == pytest.approx(second, rel=1e-12, abs=1e-12)


def _assert_parity(window, algo="new", epsilon=0.5):
    ref = SuddennessImpulsivityReference(direction_change_epsilon=epsilon, suddenness_algo=algo)
    new = SuddennessImpulsivity(window=max(len(window), 6), dims=window.shape[2], direction_change_epsilon=epsilon,
                                algorithm=ENUM[algo])
    reference_result, new_result = ref.compute(window), new._process_window(_series(window))
    if reference_result.ok and not np.isfinite(window).all():  # data problem: INVALID_INPUT instead of OK with NaN
        assert new_result.status == Status.INVALID_INPUT
        return reference_result
    if reference_result.ok and SuddennessReference(algo=algo).compute(window).alpha == -1:
        assert new_result.status == Status.INVALID_INPUT  # the quantile fit failed (#47): INVALID_INPUT, the index kept
    else:
        assert reference_result.status == new_result.status
    if reference_result.ok:
        assert _same(reference_result.impulsivity_index, new_result.impulsivity_index), (reference_result.impulsivity_index, new_result.impulsivity_index)
    return reference_result


@pytest.mark.parametrize("algo", ALGOS)
@pytest.mark.parametrize("seed", range(50))
def test_random_windows(seed, algo):
    rng = np.random.default_rng(seed)
    frames, dims = int(rng.integers(6, 60)), int(rng.integers(2, 4))
    walk = np.cumsum(rng.standard_normal((frames, 1, dims)) * rng.uniform(0.1, 2), axis=0)
    _assert_parity(walk, algo, epsilon=float(rng.choice([0.5, 0.2, 5.0, 0.01])))


@pytest.mark.parametrize("algo", ALGOS)
def test_nonzero_impulsivity_is_exercised(algo):
    rng = np.random.default_rng(11)
    nonzero = 0
    for _ in range(80):
        window = np.cumsum(rng.standard_normal((20, 1, 2)), axis=0)
        nonzero += _assert_parity(window, algo, epsilon=1.0).impulsivity_index > 0
    assert nonzero > 0


@pytest.mark.parametrize("algo", ALGOS)
@pytest.mark.parametrize("frames", range(0, 9))
def test_short_windows(frames, algo):
    window = np.random.default_rng(frames).standard_normal((frames, 1, 3))
    result = _assert_parity(window, algo)
    assert (result.status == Status.WARMING_UP) == (frames < 6)


def test_a_position_has_two_or_three_coordinates():
    """A one-dimensional trajectory has no direction change: rejected at construction, like any dimension but 2 or 3;
    a `(signals, dims)` frame is rejected by the shape check."""
    for dims in (1, 4):
        with pytest.raises(ValueError, match="2 or 3 coordinates"):
            SuddennessImpulsivity(window=8, dims=dims)
        with pytest.raises(ValueError, match="2 or 3 coordinates"):
            SuddennessImpulsivity(window=8).process(np.zeros(dims))
    with pytest.raises(ValueError, match="SuddennessImpulsivity"):
        SuddennessImpulsivity(window=8).process(np.zeros((3, 2)))
    for frames in (0, 1, 2):  # fewer frames than the minimum window: warming up
        assert SuddennessImpulsivity(window=6, dims=2)._process_window(np.zeros((2, frames))).status == Status.WARMING_UP


@pytest.mark.parametrize("algo", ALGOS)
def test_degenerate_windows(algo):
    for window in (np.zeros((10, 1, 3)), np.ones((10, 1, 2)), np.cumsum(np.ones((10, 1, 2)), axis=0),
                   np.tile([[0.0, 0.0], [1.0, 0.0]], (5, 1))[:, None, :]):
        _assert_parity(window, algo)


@pytest.mark.parametrize("algo", ALGOS)
def test_nan_and_inf_windows(algo):
    rng = np.random.default_rng(3)
    window = np.cumsum(rng.standard_normal((20, 1, 2)), axis=0)
    for bad in (np.nan, np.inf):
        broken_window = window.copy()
        broken_window[10, 0, 1] = bad
        with np.errstate(all="ignore"):
            _assert_parity(broken_window, algo)


def test_the_quantile_sentinel_is_invalid_input_and_keeps_the_index():
    """#47: SuddennessImpulsivity could not see the alpha = -1 sentinel of the QUANTILE fit (OK with an index); it reads the
    alpha of the suddenness fit now and reports INVALID_INPUT like Suddenness, with the same numbers."""
    failed = 0
    for seed in range(40):
        series = np.cumsum(np.random.default_rng(seed).standard_normal((3, 12)), axis=1)
        index = SuddennessImpulsivity(window=12, dims=3, algorithm="quantile", direction_change_epsilon=2.0)._process_window(series)
        fit = Suddenness(window=12, dims=3, algorithm="quantile")._process_window(series)
        assert index.status == fit.status
        if fit.alpha == -1:
            failed += 1
            assert index.status == Status.INVALID_INPUT and index.reason == fit.reason and np.isfinite(index.impulsivity_index)
        else:
            assert index.ok
        assert SuddennessImpulsivity(window=12, dims=3, direction_change_epsilon=2.0)._process_window(series).ok
    assert failed > 0


def test_both_components_evaluate_the_same_trajectory():
    """The index is the cosine direction change times the suddenness verdict of one and the same trajectory."""
    rng = np.random.default_rng(4)
    for algorithm in ("constrained", "quantile"):
        series = np.cumsum(rng.standard_normal((2, 20)), axis=1)
        index = SuddennessImpulsivity(window=20, dims=2, algorithm=algorithm)._process_window(series).impulsivity_index
        cosine = DirectionChange(window=20, metrics=["cosine"])._process_window(series).cosine
        sudden = Suddenness(window=20, dims=2, algorithm=algorithm)._process_window(series).is_sudden
        assert index == pytest.approx(cosine * float(sudden), rel=1e-12, abs=1e-15)


def test_parameter_properties():
    feature = SuddennessImpulsivity(window=15, dims=2, direction_change_epsilon=0.3, algorithm="quantile")
    assert feature.direction_change_epsilon == 0.3 and feature.algorithm == "quantile"
    feature.direction_change_epsilon = 2
    feature.algorithm = "constrained"
    assert feature.direction_change_epsilon == 2.0 and feature.algorithm == "constrained"
    window = np.cumsum(np.random.default_rng(5).standard_normal((15, 1, 2)), axis=0)
    ref = SuddennessImpulsivityReference(direction_change_epsilon=2, suddenness_algo="new").compute(window)
    assert feature._process_window(_series(window)).impulsivity_index == pytest.approx(ref.impulsivity_index, rel=1e-12)


REFERENCE = np.load(Path(__file__).resolve().parents[1] / "data" / "impulsivity_reference.npz")
META = json.loads(str(REFERENCE["meta"]))
RENAMED = {"threshold": "peak_threshold"}


def _bits(values):
    values = np.asarray(values, dtype=float)
    return np.where(np.isnan(values), np.nan, values).view(np.int64)


def _check_against_reference(prefix, scenario, feature, samples):
    """Feed `samples` one by one, applying the events of the scenario, and compare every result with the frozen one."""
    events = {int(key): value for key, value in scenario.get("events", {}).items()}
    values, status, reason = REFERENCE[prefix + "_values"], REFERENCE[prefix + "_status"], REFERENCE[prefix + "_reason"]
    for index, sample in enumerate(samples):
        for event in events.get(index, []):
            feature.reset() if event[0] == "reset" else setattr(feature, RENAMED.get(event[1], event[1]), event[2])
        result = feature.process(*sample)
        assert int(result.status) == status[index] and result.reason == reason[index], (prefix, index)
        got = [float(result[name]) for name in result.schema.names]
        assert np.array_equal(_bits(got), _bits(np.atleast_1d(values[index]))), (prefix, index, got, values[index])
    assert len(values) == len(samples)


@pytest.mark.parametrize("scenario", META["scenarios"], ids=[scenario["name"] for scenario in META["scenarios"]])
def test_contraction_impulsivity_reproduces_the_frozen_outputs(scenario):
    params = {RENAMED.get(name, name): value for name, value in scenario["params"].items()}
    samples = list(zip(REFERENCE[scenario["sqom"]], REFERENCE[scenario["ci"]]))
    _check_against_reference("imp_" + scenario["name"], scenario, ContractionImpulsivity(**params), samples)


@pytest.mark.parametrize("scenario", META["sudden"], ids=[scenario["name"] for scenario in META["sudden"]])
def test_suddenness_impulsivity_reproduces_the_frozen_outputs(scenario):
    frames = [(frame,) for frame in REFERENCE[scenario["data"]]]
    _check_against_reference("sud_" + scenario["name"], scenario, SuddennessImpulsivity(**scenario["params"]), frames)


def test_the_reference_exercises_both_features():
    assert sum(int((REFERENCE[f"imp_{s['name']}_values"][:, 0] != 0).sum()) for s in META["scenarios"]) > 100
    statuses = np.concatenate([REFERENCE[f"sud_{s['name']}_status"] for s in META["sudden"]])
    assert {int(Status.OK), int(Status.WARMING_UP), int(Status.INVALID_INPUT)} <= set(statuses.tolist())
    assert sum(int((np.nan_to_num(REFERENCE[f"sud_{s['name']}_values"]) != 0).sum()) for s in META["sudden"]) > 100


def test_motion_threshold_is_a_parameter_with_the_old_default():
    assert inspect.signature(ContractionImpulsivity).parameters["motion_threshold"].default == 0.01
    pause = ContractionImpulsivity(peak_threshold=0.0, motion_threshold=0.1).process(0.05, 0.5)
    assert pause.gesture_duration == 1.0  # 0.05 is a pause for the new threshold, motion for the default
    assert ContractionImpulsivity(peak_threshold=0.0).process(0.05, 0.5).gesture_duration == 0.0
    with pytest.raises(ValueError):
        ContractionImpulsivity(motion_threshold=1.5)
