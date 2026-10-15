"""Both impulsivity features against the frozen outputs
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

from pyeyesweb.data_models.results import Status  # noqa: E402
from pyeyesweb.low_level import DirectionChange  # noqa: E402
from pyeyesweb.mid_level import ContractionImpulsivity, Suddenness, SuddennessImpulsivity  # noqa: E402


@pytest.mark.parametrize("frames", range(0, 9))
@pytest.mark.parametrize("method", ["constrained", "quantile"])
def test_short_windows(frames, method):
    series = np.random.default_rng(frames).standard_normal((3, frames))
    result = SuddennessImpulsivity(window=6, dims=3, method=method)._process_window(series)
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

def test_the_quantile_sentinel_is_invalid_input_without_an_index():
    """#47: SuddennessImpulsivity could not see the alpha = -1 sentinel of the QUANTILE fit (OK with an index); it reads the
    alpha of the suddenness fit now and reports INVALID_INPUT like Suddenness, with the reason and no numbers."""
    failed = 0
    for seed in range(40):
        series = np.cumsum(np.random.default_rng(seed).standard_normal((3, 12)), axis=1)
        index = SuddennessImpulsivity(window=12, dims=3, method="quantile", direction_change_epsilon=2.0)._process_window(series)
        fit = Suddenness(window=12, dims=3, method="quantile")._process_window(series)
        assert index.status == fit.status
        if fit.status == Status.INVALID_INPUT:
            failed += 1
            assert index.status == Status.INVALID_INPUT and index.reason == fit.reason and np.isnan(index.impulsivity_index)
        else:
            assert index.ok
        assert SuddennessImpulsivity(window=12, dims=3, direction_change_epsilon=2.0)._process_window(series).ok
    assert failed > 0


def test_both_components_evaluate_the_same_trajectory():
    """The index is the cosine direction change times the suddenness verdict of one and the same trajectory."""
    rng = np.random.default_rng(4)
    for algorithm in ("constrained", "quantile"):
        series = np.cumsum(rng.standard_normal((2, 20)), axis=1)
        index = SuddennessImpulsivity(window=20, dims=2, method=algorithm)._process_window(series).impulsivity_index
        cosine = DirectionChange(window=20, metrics=["cosine"])._process_window(series).cosine
        sudden = Suddenness(window=20, dims=2, method=algorithm)._process_window(series).is_sudden
        if math.isnan(index):  # the quantile fit failed: no number
            continue
        assert index == pytest.approx(cosine * float(sudden), rel=1e-12, abs=1e-15)


def test_parameter_properties():
    feature = SuddennessImpulsivity(window=15, dims=2, direction_change_epsilon=0.3, method="quantile")
    assert feature.direction_change_epsilon == 0.3 and feature.method == "quantile"
    feature.direction_change_epsilon = 2
    feature.method = "constrained"
    assert feature.direction_change_epsilon == 2.0 and feature.method == "constrained"


REFERENCE = np.load(Path(__file__).resolve().parents[1] / "data" / "impulsivity_reference.npz")
META = json.loads(str(REFERENCE["meta"]))
# the names of the frozen scenarios (the former feature) -> the names today
RENAMED = {"threshold": "peak_threshold", "ges_dur": "gesture_duration", "frames": "sampling_rate", "algorithm": "method"}


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
    params = {"sampling_rate": 25.0}  # the frame rate that was the default
    params |= {RENAMED.get(name, name): value for name, value in scenario["params"].items()}
    samples = list(zip(REFERENCE[scenario["sqom"]], REFERENCE[scenario["ci"]]))
    _check_against_reference("imp_" + scenario["name"], scenario, ContractionImpulsivity(**params), samples)


@pytest.mark.parametrize("scenario", META["sudden"], ids=[scenario["name"] for scenario in META["sudden"]])
def test_suddenness_impulsivity_reproduces_the_frozen_outputs(scenario):
    frames = [(frame,) for frame in REFERENCE[scenario["data"]]]
    _check_against_reference("sud_" + scenario["name"], scenario, SuddennessImpulsivity(**{RENAMED.get(name, name): value for name, value in scenario["params"].items()}), frames)


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
