"""Minimum windows, input validation and declared types of the analysis primitives (statistics, complexity, rarity)."""
import os
import sys

import numpy as np
import pytest

if os.environ.get("EYESWEB_CORE_PATH"):
    sys.path.insert(0, os.environ["EYESWEB_CORE_PATH"])

pytest.importorskip("pyeyesweb._core", exc_type=ImportError)

from pyeyesweb.analysis_primitives import (  # noqa: E402
    CoarseGraining, MultiScaleEntropy, Periodicity, Rarity, SampleEntropy
)

RNG = np.random.default_rng(0)


def test_multi_scale_entropy_rejects_a_window_that_drops_scales():
    with pytest.raises(ValueError, match="3000"):
        MultiScaleEntropy(window=2999)
    feature = MultiScaleEntropy(window=1000, max_scale=2)
    for name, value in (("max_scale", 3), ("minimum_points", 501), ("window", 999)):
        with pytest.raises(ValueError, match="window must be >="):
            setattr(feature, name, value)
    assert (feature.window, feature.max_scale, feature.minimum_points) == (1000, 2, 500)
    feature.window = 3000
    feature.max_scale = 6
    assert feature.max_scale == 6


@pytest.mark.parametrize("build,minimum", [
    (lambda window_size: Rarity(method="mode_distance", window=window_size), 2),
    (lambda window_size: SampleEntropy(window=window_size, embedding_dimension=4), 5),
    (lambda window_size: SampleEntropy(window=window_size), 13),
    (lambda window_size: CoarseGraining(window=window_size, factor=3), 3),
    (lambda window_size: CoarseGraining(window=window_size), 2),
    (lambda window_size: Periodicity(window=window_size), 2),
])
def test_minimum_window_at_construction_and_when_set(build, minimum):
    with pytest.raises(ValueError, match=f">= {minimum}"):
        build(minimum - 1)
    feature = build(minimum)
    with pytest.raises(ValueError, match=f">= {minimum}"):
        feature.window = minimum - 1
    assert feature.window == minimum


def test_sample_entropy_and_coarse_graining_revalidate_on_parameter_change():
    entropy = SampleEntropy(window=8, embedding_dimension=3)
    with pytest.raises(ValueError, match=">= 9"):
        entropy.embedding_dimension = 8
    assert entropy.embedding_dimension == 3 and entropy.outputs["sample_entropy"].shape == (3,)
    entropy.embedding_dimension = 7
    assert entropy.outputs["sample_entropy"].shape == (7,)
    assert entropy._process_window(RNG.standard_normal((1, 8))).ok
    graining = CoarseGraining(window=6, factor=2)
    with pytest.raises(ValueError, match=">= 7"):
        graining.factor = 7
    graining.factor = 3
    assert graining._process_window(RNG.standard_normal((1, 6))).coarse_grained.shape == (1, 2)


def test_rarity_method_accepts_its_name():
    for method in ("mode_distance", "MODE_DISTANCE", "mode-distance"):
        assert Rarity(method=method, window=5).method == "mode_distance"
    assert Rarity(method="Information").method == "information"
    with pytest.raises(ValueError, match="'information'.*'mode_distance'|'mode_distance'.*'information'"):
        Rarity(method="nope")


def test_histogram_rarity_alpha_must_be_positive():
    feature = Rarity(method="mode_distance", window=5)
    for bad in (0, -1.0):
        with pytest.raises(ValueError):
            Rarity(method="mode_distance", window=5, alpha=bad)
        with pytest.raises(ValueError):
            feature.alpha = bad
    feature.alpha = 2
    assert feature.alpha == 2.0


def test_periodicity_has_no_sampling_rate():
    with pytest.raises(Exception):
        Periodicity(window=16, sampling_rate=100.0)
    assert not hasattr(Periodicity(window=16), "sampling_rate")
