"""Minimum windows, algorithm enum, input kinds and data problems of Suddenness, SuddennessImpulsivity
and GestureSegmenter."""
import numpy as np
import pytest

from pyeyesweb.data_models.inputs import InputKind
from pyeyesweb.data_models.results import Status
from pyeyesweb.low_level import MotionNoiseDetector
from pyeyesweb.mid_level import GestureSegmenter, Suddenness, SuddennessImpulsivity

FITS = [Suddenness, SuddennessImpulsivity]


def _series(frames, dims=3, seed=0):
    """A random walk of one point as the `(dims, frames)` series of `_process_window`."""
    walk = np.cumsum(np.random.default_rng(seed).standard_normal((frames, dims)), axis=0)
    return walk.T


@pytest.mark.parametrize("cls, minimum", [(Suddenness, 6), (SuddennessImpulsivity, 6)])
def test_minimum_window_is_validated(cls, minimum):
    with pytest.raises(ValueError, match=f">= {minimum}"):
        cls(window=minimum - 1)
    feature = cls(window=minimum)
    with pytest.raises(ValueError, match=f">= {minimum}"):
        feature.window = minimum - 1
    assert feature.window == minimum


@pytest.mark.parametrize("cls", FITS)
def test_inputs_are_one_point(cls):
    assert cls(window=8, dims=2).inputs[0].kind is InputKind.SAMPLE


@pytest.mark.parametrize("cls", FITS)
def test_algorithm_enum_and_runtime_change(cls):
    feature = cls(window=8)
    assert feature.algorithm == "constrained"
    feature.algorithm = "quantile"
    assert feature.algorithm == "quantile"
    assert cls(window=8, algorithm="quantile").algorithm == "quantile"
    for bad in ("new", "whatever", 3):
        with pytest.raises(ValueError, match="constrained.*quantile"):
            cls(window=8, algorithm=bad)
        with pytest.raises(ValueError, match="constrained.*quantile"):
            feature.algorithm = bad


@pytest.mark.parametrize("cls", FITS)
def test_short_series_is_warming_up_with_the_real_cause(cls):
    result = cls(window=8, dims=3)._process_window(_series(4))
    assert result.status == Status.WARMING_UP and "fewer than 6 frames" in result.reason


@pytest.mark.parametrize("cls", FITS)
@pytest.mark.parametrize("bad", [np.nan, np.inf])
def test_non_finite_positions_are_invalid_input(cls, bad):
    series = _series(12)
    series[0, 5] = bad
    assert cls(window=12, dims=3)._process_window(series).status == Status.INVALID_INPUT


def test_quantile_sentinel_is_invalid_input_and_keeps_the_numbers():
    feature = Suddenness(window=12, dims=3, algorithm="quantile")
    statuses = []
    for seed in range(20):
        result = feature._process_window(_series(12, seed=seed))
        statuses.append(result.status)
        if result.alpha == -1:
            assert result.status == Status.INVALID_INPUT and result.reason and np.isfinite(result.gamma)
        else:
            assert result.ok
    assert Status.INVALID_INPUT in statuses
    assert Suddenness(window=12, dims=3)._process_window(_series(12)).ok


def test_motion_noise_detector_non_finite_coordinates_are_invalid_input():
    detector = MotionNoiseDetector(labels=["a", "b"])
    result = detector.process(np.array([[np.nan, 0, 0], [1, 1, 1]]), timestamp=0.0)
    assert result.status == Status.INVALID_INPUT
    assert detector.process({"a": (np.inf, 0, 0), "b": (1, 1, 1)}, timestamp=0.1).status == Status.INVALID_INPUT
    assert detector.process(np.zeros((2, 3)), timestamp=0.2).status == Status.OK


def test_gesture_segmenter_non_finite_samples_are_invalid_input_and_leave_the_state():
    segmenter = GestureSegmenter(filter_window_length=5)
    for value, noise in ((np.nan, 0.0), (np.inf, 0.0), (1.0, np.nan), ([], 0.0)):
        assert segmenter.process(value, noise).status == Status.INVALID_INPUT
    reference = GestureSegmenter(filter_window_length=5)
    for _ in range(11):
        assert segmenter.process(1.0).status == reference.process(1.0).status
