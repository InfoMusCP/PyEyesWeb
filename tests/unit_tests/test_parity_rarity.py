"""Rarity(MODE_DISTANCE) (compiled core): short windows, non-finite samples, alpha.

Needs the compiled core: found as pyeyesweb._eyesweb_core, or as eyesweb_core in EYESWEB_CORE_PATH; else skipped.
"""
import os
import sys

import numpy as np
import pytest

if os.environ.get("EYESWEB_CORE_PATH"):
    sys.path.insert(0, os.environ["EYESWEB_CORE_PATH"])

pytest.importorskip("pyeyesweb._core", exc_type=ImportError)

from pyeyesweb.analysis_primitives import Rarity  # noqa: E402
from pyeyesweb.data_models.results import Status  # noqa: E402


@pytest.mark.parametrize("count", range(0, 12))
def test_short_windows(count):
    window = np.random.default_rng(count).standard_normal(count)
    result = Rarity(method="mode_distance", window=10)._process_window(window)
    assert (result.status == Status.WARMING_UP) == (count < 2)


@pytest.mark.parametrize("bad", [np.nan, np.inf, -np.inf])
def test_non_finite_samples_are_invalid_input(bad):
    window = np.array([0.0, 1.0, bad, 2.0])
    result = Rarity(method="mode_distance", window=4)._process_window(window)
    assert result.status is Status.INVALID_INPUT and np.isnan(result.rarity)


def test_alpha_property_and_scaling():
    feature = Rarity(method="mode_distance", window=50, alpha=1.0)
    window = np.random.default_rng(2).standard_normal(50)
    base = feature._process_window(window).rarity
    feature.alpha = 2.0
    assert feature.alpha == 2.0
    assert feature._process_window(window).rarity == pytest.approx(2 * base, rel=1e-15)
