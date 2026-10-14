"""Parity of Suddenness (compiled core) with the preserved pure-Python implementation.

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
from suddenness_reference import SuddennessReference  # noqa: E402

from pyeyesweb.data_models.results import Status  # noqa: E402
from pyeyesweb.mid_level import Suddenness  # noqa: E402

OUTPUTS = ["alpha", "beta", "gamma"]


def _series(window):
    """A `(Time, 1, N_dims)` tensor (the reference takes a signals axis) as the `(N_dims, Time)` series of the one point
    `_process_window` takes."""
    return np.asarray(window)[:, 0, :].T


def _same(first, second):
    if isinstance(first, float) and math.isnan(first):
        return isinstance(second, float) and math.isnan(second)
    return first == pytest.approx(second, rel=1e-12, abs=1e-12)


ENUM = {"new": "constrained", "old": "quantile"}


def _assert_parity(window, algo):
    ref, new = SuddennessReference(algo=algo), Suddenness(window=max(len(window), 6), dims=window.shape[2],
                                                          algorithm=ENUM[algo])
    reference_result, new_result = ref.compute(window), new._process_window(_series(window))
    if reference_result.ok and not np.isfinite(window[:, 0]).all():  # data problem: INVALID_INPUT instead of OK with NaN
        assert new_result.status == Status.INVALID_INPUT
        return new_result
    if reference_result.ok and reference_result.alpha == -1:  # the quantile fit failed: INVALID_INPUT, no numbers
        assert new_result.status == Status.INVALID_INPUT
        assert not any(new_result.valid.values())
        return new_result
    assert reference_result.status == new_result.status
    if reference_result.ok:
        assert reference_result.is_sudden == new_result.is_sudden
        for name in OUTPUTS:
            assert _same(getattr(reference_result, name), getattr(new_result, name)), (name, getattr(reference_result, name), getattr(new_result, name))
    return new_result


def _walk(speeds, dims, rng):
    steps = rng.standard_normal((len(speeds), dims))
    steps *= (np.asarray(speeds) / np.linalg.norm(steps, axis=1))[:, None]
    pos = np.vstack([np.zeros(dims), np.cumsum(steps, axis=0)])
    return pos[:, None, :]


ALGOS = ["new", "old"]


@pytest.mark.parametrize("algo", ALGOS)
@pytest.mark.parametrize("seed", range(60))
@pytest.mark.parametrize("kind", ["gamma", "cauchy", "lognormal", "uniform"])
def test_random_windows(seed, kind, algo):
    rng = np.random.default_rng(seed)
    count = int(rng.integers(6, 80))
    dims = int(rng.integers(2, 4))
    speeds = {
        "gamma": rng.gamma(2.0, 1.0, count - 1),
        "cauchy": np.abs(rng.standard_cauchy(count - 1)),
        "lognormal": rng.lognormal(0, 2, count - 1),
        "uniform": rng.uniform(0, 1, count - 1),
    }[kind]
    _assert_parity(_walk(speeds, dims, rng), algo)


@pytest.mark.parametrize("algo", ALGOS)
@pytest.mark.parametrize("count", range(0, 8))
def test_short_windows(count, algo):
    rng = np.random.default_rng(count)
    result = _assert_parity(rng.standard_normal((count, 1, 3)), algo)
    assert (result.status == Status.WARMING_UP) == (count < 6)


@pytest.mark.parametrize("algo", ALGOS)
def test_constant_and_degenerate_windows(algo):
    still = np.zeros((20, 1, 3))
    uniform_motion = np.cumsum(np.ones((20, 1, 3)), axis=0)
    steps = np.stack([np.cumsum(np.tile([0.0, 1.0], 10)), np.zeros(20)], axis=1)[:, None, :]
    for window in (still, uniform_motion, steps, still + 5.0):
        _assert_parity(window, algo)


@pytest.mark.parametrize("algo", ALGOS)
def test_nan_and_inf_windows(algo):
    rng = np.random.default_rng(3)
    window = rng.standard_normal((30, 1, 3))
    nan_window = window.copy()
    nan_window[10, 0, 1] = np.nan
    inf_window = window.copy()
    inf_window[10, 0, 0] = np.inf
    for broken_window in (nan_window, inf_window):
        with np.errstate(all="ignore"):
            _assert_parity(broken_window, algo)


def test_one_point_per_frame_with_two_or_three_coordinates():
    """A `(signals, dims)` frame is rejected by the shape check, and so is any dimension but 2 or 3."""
    with pytest.raises(ValueError, match="Suddenness"):
        Suddenness(window=25).process(np.zeros((3, 2)))
    for dims in (1, 4):
        with pytest.raises(ValueError, match="2 or 3 coordinates"):
            Suddenness(window=25, dims=dims)
        with pytest.raises(ValueError, match="2 or 3 coordinates"):
            Suddenness(window=25).process(np.zeros(dims))
