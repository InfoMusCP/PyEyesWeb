"""Suddenness (compiled core): window rules and the input shape.

Needs the compiled core: found as pyeyesweb._eyesweb_core, or as eyesweb_core in EYESWEB_CORE_PATH; else skipped.
"""
import os
import sys

import numpy as np
import pytest

if os.environ.get("EYESWEB_CORE_PATH"):
    sys.path.insert(0, os.environ["EYESWEB_CORE_PATH"])

pytest.importorskip("pyeyesweb._core", exc_type=ImportError)

from pyeyesweb.data_models.results import Status  # noqa: E402
from pyeyesweb.mid_level import Suddenness  # noqa: E402

METHODS = ["constrained", "quantile"]


@pytest.mark.parametrize("method", METHODS)
@pytest.mark.parametrize("count", range(0, 8))
def test_short_windows(count, method):
    series = np.random.default_rng(count).standard_normal((3, count))
    result = Suddenness(window=6, dims=3, method=method)._process_window(series)
    assert (result.status == Status.WARMING_UP) == (count < 6)


@pytest.mark.parametrize("method", METHODS)
@pytest.mark.parametrize("bad", [np.nan, np.inf])
def test_non_finite_windows_are_invalid_input(method, bad):
    series = np.random.default_rng(3).standard_normal((3, 30))
    series[1, 10] = bad
    with np.errstate(all="ignore"):
        result = Suddenness(window=30, dims=3, method=method)._process_window(series)
    assert result.status == Status.INVALID_INPUT


def test_one_point_per_frame_with_two_or_three_coordinates():
    """A `(signals, dims)` frame is rejected by the shape check, and so is any dimension but 2 or 3."""
    with pytest.raises(ValueError, match="Suddenness"):
        Suddenness(window=25).process(np.zeros((3, 2)))
    for dims in (1, 4):
        with pytest.raises(ValueError, match="2 or 3 coordinates"):
            Suddenness(window=25, dims=dims)
        with pytest.raises(ValueError, match="2 or 3 coordinates"):
            Suddenness(window=25).process(np.zeros(dims))
