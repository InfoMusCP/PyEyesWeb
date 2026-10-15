"""SpectralArcLength, LogDimensionlessJerk, Harmonicity and SubmovementCount (compiled core): window rules, parameters.

Needs the compiled core: found as pyeyesweb._eyesweb_core, or as eyesweb_core in EYESWEB_CORE_PATH; else skipped.
"""
import os
import sys

import numpy as np
import pytest

if os.environ.get("EYESWEB_CORE_PATH"):
    sys.path.insert(0, os.environ["EYESWEB_CORE_PATH"])

pytest.importorskip("pyeyesweb._core", exc_type=ImportError)

from pyeyesweb.low_level import Harmonicity, LogDimensionlessJerk, SpectralArcLength, SubmovementCount  # noqa: E402

def _features(window, sampling_rate):
    """The four classes on one window."""
    shared = dict(window=window, sampling_rate=sampling_rate)
    return {
        "sparc": SpectralArcLength(**shared),
        "ldlj_v": LogDimensionlessJerk(**shared, input_mode="velocity"),
        "ldlj_a": LogDimensionlessJerk(**shared, input_mode="acceleration"),
        "harmonicity": Harmonicity(**shared),
        "n_submovements": SubmovementCount(**shared),
    }


def _bumps(count, rng):
    signal = np.arange(count)
    centres = rng.uniform(0.1, 0.9, rng.integers(1, 4)) * count
    return sum(rng.uniform(20, 100) * np.exp(-((signal - centre) / (count / 12)) ** 2) for centre in centres)


@pytest.mark.parametrize("count", [0, 1, 9])
def test_warming_up_below_ten_samples(count):
    for feature in _features(10, 50.0).values():
        result = feature._process_window(np.ones(count))
        assert result.status.name == "WARMING_UP" and "10" in result.reason


def test_window_must_hold_ten_samples():
    for build in (SpectralArcLength, LogDimensionlessJerk, Harmonicity, SubmovementCount):
        with pytest.raises(ValueError, match=">= 10"):
            build(window=9, sampling_rate=50.0)


def test_one_dimensional_profile_only():
    with pytest.raises(ValueError, match="1 channels"):
        Harmonicity(sampling_rate=50.0)._process_window(np.ones((2, 30)))


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
    assert before != feature._process_window(signal).spectral_arc_length
