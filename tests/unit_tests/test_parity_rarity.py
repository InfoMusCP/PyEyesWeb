"""Parity of Rarity(MODE_DISTANCE) (compiled core) with the preserved pure-Python implementation.

Needs the compiled core: found as pyeyesweb._eyesweb_core, or as eyesweb_core in EYESWEB_CORE_PATH; else skipped.
"""
import os
import sys

import numpy as np
import pytest

if os.environ.get("EYESWEB_CORE_PATH"):
    sys.path.insert(0, os.environ["EYESWEB_CORE_PATH"])

pytest.importorskip("pyeyesweb._core", exc_type=ImportError)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "reference"))
from rarity_reference import HistogramRarityReference  # noqa: E402

from pyeyesweb.analysis_primitives import Rarity  # noqa: E402
from pyeyesweb.data_models.results import Status  # noqa: E402


def _assert_parity(window, alpha=0.5):
    reference_result = HistogramRarityReference(alpha=alpha).compute(window)
    new_result = Rarity(method="mode_distance", window=10, alpha=alpha)._process_window(np.ravel(window))
    assert reference_result.status == new_result.status
    if reference_result.ok:
        assert reference_result.rarity == new_result.rarity  # bit for bit: same operations as numpy
    else:
        assert reference_result.reason == new_result.reason
    return new_result


@pytest.mark.parametrize("seed", range(150))
def test_random_windows(seed):
    rng = np.random.default_rng(seed)
    count = int(rng.integers(2, 400))
    kind = seed % 5
    data = [rng.standard_normal(count), rng.uniform(0, 1, count), rng.lognormal(0, 2, count),
            np.round(rng.standard_normal(count), 1), rng.integers(0, 4, count).astype(float)][kind]
    _assert_parity(data, alpha=float(rng.uniform(0.1, 3)))


@pytest.mark.parametrize("count", range(0, 12))
def test_short_windows(count):
    result = _assert_parity(np.random.default_rng(count).standard_normal(count))
    assert (result.status == Status.WARMING_UP) == (count < 2)


def test_multidimensional_windows_are_flattened():
    rng = np.random.default_rng(1)
    for shape in ((10, 3), (7, 2, 3), (30, 1, 1), (4, 5)):
        _assert_parity(rng.standard_normal(shape))
    _assert_parity(rng.standard_normal((9, 4))[:, ::2])  # non-contiguous view


def test_constant_and_edge_windows():
    for window in (np.zeros(10), np.full(10, 3.0), np.full(2, -7.0), np.array([1.0, 1.0, 1.0, 2.0]),
                   np.array([0.0, 1.0]), np.array([5.0, 0.0, 0.0, 0.0, 5.0]), np.full(16, 1e12) + np.arange(16),
                   np.linspace(0, 1, 100), np.linspace(1, 0, 100), np.array([1e-300, 0.0, 1e-300, 1e-300])):
        _assert_parity(window)


@pytest.mark.parametrize("bad", [np.nan, np.inf, -np.inf])
def test_non_finite_samples_raise_like_numpy_and_are_invalid_input_in_the_wrapper(bad):
    window = np.array([0.0, 1.0, bad, 2.0])
    with pytest.raises(ValueError):
        HistogramRarityReference().compute(window)
    result = Rarity(method="mode_distance", window=4)._process_window(window)
    assert result.status is Status.INVALID_INPUT and np.isnan(result.rarity)


def test_alpha_property_and_scaling():
    feature = Rarity(method="mode_distance", window=50, alpha=1.0)
    window = np.random.default_rng(2).standard_normal(50)
    base = feature._process_window(window).rarity
    feature.alpha = 2.0
    assert feature.alpha == 2.0
    assert feature._process_window(window).rarity == pytest.approx(2 * base, rel=1e-15)
