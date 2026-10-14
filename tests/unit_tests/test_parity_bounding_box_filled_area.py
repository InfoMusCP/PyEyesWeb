"""Parity of the core-backed BoundingBoxFilledArea (own 3D convex hull) with the preserved scipy/Qhull reference
(tests/reference/contraction_reference.py), on random clouds and on degenerate frames. Needs the compiled core
(EYESWEB_CORE_PATH), else skipped.
"""
import itertools
import os
import sys

import numpy as np
import pytest

if os.environ.get("EYESWEB_CORE_PATH"):
    sys.path.insert(0, os.environ["EYESWEB_CORE_PATH"])
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "reference"))

pytest.importorskip("pyeyesweb._core", exc_type=ImportError)

from contraction_reference import BoundingBoxFilledAreaReference  # noqa: E402
from pyeyesweb.data_models.results import Status  # noqa: E402
from pyeyesweb.low_level import BoundingBoxFilledArea  # noqa: E402

CUBE = np.array(list(itertools.product([0.0, 1.0], repeat=3)))


def _outcome(feature, frame):
    """(status, index) of a result, or the exception class when the call raises."""
    try:
        result = feature.compute(frame) if hasattr(feature, "compute") else feature.process(frame)
    except Exception as error:
        return type(error)
    return result.status, (result["contraction_index"] if result.valid["contraction_index"] else None)


def _has_no_extent(frame):
    """The test of the block: a bounding box of area <= epsilon (the original reports it as OK with index 0)."""
    if frame.ndim != 2 or frame.shape[1] != 3 or not len(frame):
        return False
    extent = np.ptp(frame, axis=0)
    return 2 * (extent[0] * extent[1] + extent[0] * extent[2] + extent[1] * extent[2]) <= BoundingBoxFilledArea.EPSILON


def _is_degenerate(frame):
    """No extent, fewer than 4 points, or coplanar points: the 3D hull is degenerate (the original reports OK with 0)."""
    if frame.ndim != 2 or frame.shape[1] != 3 or not len(frame):
        return False
    return _has_no_extent(frame) or len(frame) < 4 or np.linalg.matrix_rank(frame - frame.mean(axis=0)) < 3


def _same(frame, tol=1e-9):
    """The wrapper gives the numbers of the original; where the 3D hull is degenerate the status is INVALID_INPUT
    (2026-10-14, issue #46 and the follow-up) and the index is empty (the original says 0)."""
    new, ref = _outcome(BoundingBoxFilledArea(), frame), _outcome(BoundingBoxFilledAreaReference(), frame)
    if isinstance(ref, tuple):
        assert isinstance(new, tuple), f"core raised {new}"
        assert new[0] == (Status.INVALID_INPUT if _is_degenerate(frame) else ref[0])
        if _is_degenerate(frame):
            assert new[1] is None
        elif ref[1] is not None:
            np.testing.assert_allclose(new[1], ref[1], rtol=0, atol=tol)
    else:  # the original raises: so must the wrapper, as ValueError where the original does
        assert not isinstance(new, tuple), f"original raised {ref}, wrapper returned {new}"
        if ref is ValueError:
            assert new is ValueError


def test_random_clouds():
    rng = np.random.default_rng(0)
    for count in (4, 5, 6, 8, 12, 25, 60, 150, 400):
        for _ in range(12):
            frame = rng.standard_normal((count, 3)) * rng.uniform(0.01, 100, 3) + rng.uniform(-1e3, 1e3, 3)
            _same(frame)


def test_structured_clouds():
    rng = np.random.default_rng(1)
    sphere = rng.standard_normal((200, 3))
    sphere /= np.linalg.norm(sphere, axis=1, keepdims=True)
    lattice = np.array(list(itertools.product(range(4), repeat=3)), dtype=float)
    frames = [
        CUBE,
        CUBE * 3.5 - 1,
        np.vstack([CUBE, CUBE.mean(0), [[0.5, 0.5, 0.0], [0.0, 0.0, 0.5]]]),  # interior, face and edge points
        np.vstack([CUBE, CUBE]),  # duplicates
        sphere,
        lattice,
        rng.integers(0, 3, (60, 3)).astype(float),  # many coplanar and duplicate points
        rng.integers(-2, 3, (30, 3)).astype(float) * 1e-3,
        rng.standard_normal((50, 3)) * np.array([1, 1, 1e-3]),  # thin slab
        np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1.0]]),  # tetrahedron
    ]
    for frame in frames:
        _same(frame)


def test_degenerate_frames_are_zero_in_both():
    """The index is 0 in both; a degenerate hull is INVALID_INPUT in the wrapper (the original: OK)."""
    rng = np.random.default_rng(2)
    plane = rng.standard_normal((20, 2)) @ rng.standard_normal((2, 3))  # planar in a random orientation
    line = np.outer(rng.standard_normal(10), rng.standard_normal(3)) + 1.0
    frames = [
        np.zeros((4, 3)),
        np.ones((7, 3)),
        CUBE[:3],
        CUBE[:1],
        np.c_[rng.standard_normal((9, 2)), np.zeros(9)],  # z = 0
        np.c_[rng.standard_normal((9, 2)), np.full(9, 5.0)],
        np.c_[rng.standard_normal(9), np.zeros(9), np.zeros(9)],
        plane,
        line,
        CUBE * 1e-5,  # bounding box below epsilon
        np.array([[0, 0, 0], [1, 1, 1], [2, 2, 2], [3, 3, 3.0]]),
    ]
    for frame in frames:
        _same(frame)
        result = BoundingBoxFilledArea().process(frame)
        assert np.isnan(result["contraction_index"]) and result.status is Status.INVALID_INPUT
        assert not _has_no_extent(frame) or "no extent" in result.reason


def test_a_box_without_extent_is_invalid_input_without_an_index():
    """#46: zero-extent frames (all points equal, a single point, collinear along one axis, below epsilon) returned OK
    with 0.0; a flat box is INVALID_INPUT too, with another reason (coplanar)."""
    for frame in (np.zeros((5, 3)), CUBE[:1], np.array([[0, 0, 0], [1, 0, 0], [2, 0, 0], [3, 0, 0.0]]), CUBE * 1e-5):
        result = BoundingBoxFilledArea().process(frame)
        assert result.status is Status.INVALID_INPUT and np.isnan(result.contraction_index) and "no extent" in result.reason
    assert BoundingBoxFilledArea().process(CUBE[[0, 1, 2, 4]]).status is Status.OK  # a tetrahedron has a 3D hull
    flat = BoundingBoxFilledArea().process(np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0], [1, 1, 0.0]]))
    assert flat.status is Status.INVALID_INPUT and "coplanar" in flat.reason  # a flat box has an area, but no 3D hull


def test_flatness_threshold_matches_qhull():
    for height in (1e-12, 1e-13, 1e-14, 1e-15, 1e-16, 0.0):
        _same(np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0], [1, 1, height]]))
        _same(np.array([[0, 0, 0], [100, 0, 0], [0, 100, 0], [100, 100, height * 100], [30, 40, 0]]))


def test_non_finite_and_odd_inputs():
    for bad in (np.nan, np.inf, -np.inf):
        for count in (2, 3, 4, 8):
            frame = CUBE[:count].copy()
            frame[1, 2] = bad
            assert BoundingBoxFilledArea().process(frame).status is Status.INVALID_INPUT
    _same(np.empty((0, 3)))
    _same(np.ones((5, 2)))  # not 3D
    # More than 3 columns: the original silently builds a 4D hull and mixes its measure with a 3D box. The wrapper
    # (documented deviation) refuses such a frame.
    with pytest.raises(ValueError):
        BoundingBoxFilledArea().process(np.random.default_rng(3).standard_normal((6, 4)))


def test_epsilon_attribute_is_used():
    class Loose(BoundingBoxFilledArea):
        EPSILON = 1e-12

    frame = CUBE * 1e-5
    assert BoundingBoxFilledArea().process(frame).status is Status.INVALID_INPUT
    np.testing.assert_allclose(Loose().process(frame)["contraction_index"], 1.0)
