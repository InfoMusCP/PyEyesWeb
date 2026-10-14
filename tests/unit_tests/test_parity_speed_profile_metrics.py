"""Parity of SpectralArcLength, LogDimensionlessJerk, Harmonicity and SubmovementCount (compiled core) with the preserved
pure-Python implementation of the original `SpeedSmoothness` (`tests/reference/`), run without its low-pass filter
(`use_filter=False`): the filter was removed from the library, the speed is used as given.

Needs the compiled core: found as pyeyesweb._eyesweb_core, or as eyesweb_core in EYESWEB_CORE_PATH; else skipped.
"""
import math
import os
import sys

import numpy as np
import pytest

if os.environ.get("EYESWEB_CORE_PATH"):
    sys.path.insert(0, os.environ["EYESWEB_CORE_PATH"])

pytest.importorskip("pyeyesweb._core", exc_type=ImportError)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "reference"))
from smoothness_reference import SpeedSmoothnessReference  # noqa: E402

from pyeyesweb.low_level import Harmonicity, LogDimensionlessJerk, SpectralArcLength, SubmovementCount  # noqa: E402

# reference metric -> output of the new class
OUTPUT = {"sparc": "spectral_arc_length", "ldlj_v": "log_dimensionless_jerk", "ldlj_a": "log_dimensionless_jerk",
          "harmonicity": "harmonicity", "n_submovements": "submovement_count"}


def _features(window, sampling_rate, sparc_amplitude_threshold=0.05, sparc_min_fc=2.0, sparc_max_fc=20.0):
    """The new class that computes each reference metric, built like the reference."""
    shared = dict(window=window, sampling_rate=sampling_rate)
    return {
        "sparc": SpectralArcLength(**shared, amplitude_threshold=sparc_amplitude_threshold,
                                   minimum_cutoff_frequency=sparc_min_fc, maximum_cutoff_frequency=sparc_max_fc),
        "ldlj_v": LogDimensionlessJerk(**shared, input_mode="velocity"),
        "ldlj_a": LogDimensionlessJerk(**shared, input_mode="acceleration"),
        "harmonicity": Harmonicity(**shared),
        "n_submovements": SubmovementCount(**shared),
    }


def _same(first, second):
    if isinstance(first, float) and math.isnan(first):
        return isinstance(second, float) and math.isnan(second)
    return first == pytest.approx(second, rel=1e-9, abs=1e-9)


def _assert_parity(signal, sampling_rate=50.0, **kwargs):
    signal = np.asarray(signal, dtype=float)
    reference = SpeedSmoothnessReference(rate_hz=sampling_rate, use_filter=False, **kwargs).compute(signal)
    for metric, feature in _features(max(len(signal), 10), sampling_rate, **kwargs).items():
        result = feature._process_window(signal)
        if not reference.ok:
            assert result.status.name == reference.status.name
        elif not np.isfinite(signal).all():
            assert result.status.name == "INVALID_INPUT"
        else:
            expected = getattr(reference, metric)
            assert _same(expected, result[OUTPUT[metric]]), (metric, expected, result[OUTPUT[metric]])
            assert result.status.name == ("OK" if np.isfinite(expected) else "INVALID_INPUT")


def _bumps(count, rng):
    signal = np.arange(count)
    centres = rng.uniform(0.1, 0.9, rng.integers(1, 4)) * count
    return sum(rng.uniform(20, 100) * np.exp(-((signal - centre) / (count / 12)) ** 2) for centre in centres)


@pytest.mark.parametrize("seed", range(40))
def test_random_profiles(seed):
    rng = np.random.default_rng(seed)
    count = int(rng.integers(10, 200))
    rate = float(rng.choice([25.0, 50.0, 100.0, 120.0]))
    signal = _bumps(count, rng) + rng.normal(0, rng.choice([0.0, 0.5, 5.0]), count)
    _assert_parity(signal, sampling_rate=rate,
                   sparc_amplitude_threshold=float(rng.choice([0.01, 0.05, 0.2])),
                   sparc_min_fc=float(rng.choice([1.0, 2.0])), sparc_max_fc=float(rng.choice([8.0, 20.0])))


@pytest.mark.parametrize("count", [10, 11, 15, 16, 17, 30])
def test_short_windows(count):
    _assert_parity(np.abs(np.sin(np.arange(count) / 2.0)) * 50, sampling_rate=50.0)


@pytest.mark.parametrize("signal", [
    np.zeros(30), np.full(30, 7.0), np.arange(30.0), -np.arange(30.0), np.tile([0.0, 40.0], 15),
    np.r_[np.zeros(15), np.full(15, 1e-9)], np.full(30, 1e-12), np.tile([5.0, 5.0, 9.0], 10),
    np.sin(np.arange(60) / 3.0), 1e6 * np.sin(np.arange(60) / 3.0),
])
def test_degenerate_signals(signal):
    _assert_parity(signal)


def test_nan_and_inf():
    signal = np.abs(np.sin(np.arange(40) / 4.0)) * 30
    signal[7] = np.nan
    _assert_parity(signal)
    copy = signal.copy()
    copy[7] = np.inf
    _assert_parity(copy)


@pytest.mark.parametrize("count", [0, 1, 9])
def test_warming_up_below_ten_samples(count):
    for feature in _features(10, 50.0).values():
        result = feature._process_window(np.ones(count))
        assert result.status.name == "WARMING_UP" and "10" in result.reason


def test_window_must_hold_ten_samples():
    for build in (SpectralArcLength, LogDimensionlessJerk, Harmonicity, SubmovementCount):
        with pytest.raises(ValueError, match=">= 10"):
            build(window=9)


def test_one_dimensional_profile_only():
    with pytest.raises(ValueError, match="1 channels"):
        Harmonicity()._process_window(np.ones((2, 30)))


@pytest.mark.parametrize("build, parameter, value", [
    (SpectralArcLength, "sampling_rate", 0.0), (SpectralArcLength, "amplitude_threshold", 1.5),
    (SpectralArcLength, "minimum_cutoff_frequency", 0.0), (SpectralArcLength, "maximum_cutoff_frequency", 1.0),
    (LogDimensionlessJerk, "sampling_rate", -1.0), (LogDimensionlessJerk, "input_mode", "jerk"),
    (Harmonicity, "sampling_rate", 0.0), (SubmovementCount, "sampling_rate", 0.0),
    (SubmovementCount, "prominence_factor", -0.1),
])
def test_invalid_parameters_raise_at_construction(build, parameter, value):
    with pytest.raises(ValueError):
        build(**{parameter: value})


@pytest.mark.parametrize("build", [SpectralArcLength, LogDimensionlessJerk, Harmonicity, SubmovementCount])
def test_the_filter_is_gone(build):
    with pytest.raises(TypeError, match="use_filter"):
        build(use_filter=False)


def test_parameter_change_reaches_the_core():
    feature = SpectralArcLength(sampling_rate=50.0)
    signal = _bumps(80, np.random.default_rng(2))
    before = feature._process_window(signal).spectral_arc_length
    feature.maximum_cutoff_frequency = 2.5
    reference = SpeedSmoothnessReference(use_filter=False, sparc_max_fc=2.5).compute(signal).sparc
    assert feature._process_window(signal).spectral_arc_length == pytest.approx(reference, rel=1e-9)
    assert before != feature._process_window(signal).spectral_arc_length
