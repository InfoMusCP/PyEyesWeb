"""BoundingBoxFilledArea (own 3D convex hull) on degenerate and odd frames. Needs the compiled core
(EYESWEB_CORE_PATH), else skipped.
"""
import itertools
import os
import sys

import numpy as np
import pytest

if os.environ.get("EYESWEB_CORE_PATH"):
    sys.path.insert(0, os.environ["EYESWEB_CORE_PATH"])

pytest.importorskip("pyeyesweb._core", exc_type=ImportError)

from pyeyesweb.data_models.results import Status  # noqa: E402
from pyeyesweb.low_level import BoundingBoxFilledArea  # noqa: E402

CUBE = np.array(list(itertools.product([0.0, 1.0], repeat=3)))


def _has_no_extent(frame):
    """The test of the block: a bounding box of area <= epsilon (the original reports it as OK with index 0)."""
    if frame.ndim != 2 or frame.shape[1] != 3 or not len(frame):
        return False
    extent = np.ptp(frame, axis=0)
    return 2 * (extent[0] * extent[1] + extent[0] * extent[2] + extent[1] * extent[2]) <= BoundingBoxFilledArea.EPSILON



def test_degenerate_frames_are_invalid_input():
    """A degenerate hull is INVALID_INPUT with an empty index."""
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


def test_non_finite_and_odd_inputs():
    for bad in (np.nan, np.inf, -np.inf):
        for count in (2, 3, 4, 8):
            frame = CUBE[:count].copy()
            frame[1, 2] = bad
            assert BoundingBoxFilledArea().process(frame).status is Status.INVALID_INPUT
    # More than 3 columns: the wrapper refuses such a frame (it would mix a 4D hull with a 3D box).
    with pytest.raises(ValueError):
        BoundingBoxFilledArea().process(np.random.default_rng(3).standard_normal((6, 4)))


def test_epsilon_attribute_is_used():
    class Loose(BoundingBoxFilledArea):
        EPSILON = 1e-12

    frame = CUBE * 1e-5
    assert BoundingBoxFilledArea().process(frame).status is Status.INVALID_INPUT
    np.testing.assert_allclose(Loose().process(frame)["contraction_index"], 1.0)
