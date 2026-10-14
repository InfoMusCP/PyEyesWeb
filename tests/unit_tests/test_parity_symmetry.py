"""Parity of the core-backed Symmetry (REFLECTION) with the preserved NumPy reference
(tests/reference/symmetry_reference.py). Needs the compiled core: set EYESWEB_CORE_PATH (tests are skipped
otherwise)."""
import os
import sys

import numpy as np
import pytest

if os.environ.get("EYESWEB_CORE_PATH"):
    sys.path.insert(0, os.environ["EYESWEB_CORE_PATH"])
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "reference"))

pytest.importorskip("pyeyesweb._core", exc_type=ImportError)

from symmetry_reference import GeometricSymmetryReference  # noqa: E402
from pyeyesweb.data_models.results import Status  # noqa: E402
from pyeyesweb.low_level.symmetry import Symmetry  # noqa: E402
from symmetry_inputs import reflection  # noqa: E402


_NEW_NAME = {"pair_error": "pair_symmetry"}  # the reference keeps the legacy output name


def _compare(frame, pairs, tol=1e-9, **params):
    centre = params.get("center_of_symmetry", -1)  # the reference takes a row, -1 for the barycentre
    new = reflection(len(frame), pairs, None if centre == -1 else centre).process(frame)
    ref = GeometricSymmetryReference(pairs, **params).compute(frame)
    assert new.status == ref.status
    assert new.reason == ref.reason
    assert new.valid == {_NEW_NAME.get(count, count): flag for count, flag in ref.valid.items()}
    for name in ref.valid:
        np.testing.assert_allclose(new[_NEW_NAME.get(name, name)], ref[name], rtol=tol, atol=tol, equal_nan=True)
    return ref


PAIRS = [[(0, 1)], [(0, 1), (2, 3)], [(3, 2), (0, 1), (3, 2), (1, 0)], [(0, 0)], [(4, 5), (0, 3), (1, 2)]]
CENTRES = [{}, {"center_of_symmetry": 0}, {"center_of_symmetry": 5}, {"center_of_symmetry": -1}]


@pytest.mark.parametrize("pairs", PAIRS)
@pytest.mark.parametrize("centre", CENTRES)
@pytest.mark.parametrize("dims", [1, 2, 3, 4])
def test_random_frames(pairs, centre, dims):
    rng = np.random.default_rng(17)
    for _ in range(50):
        _compare(rng.standard_normal((6, dims)) * 30, pairs, **centre)


@pytest.mark.parametrize("pairs", PAIRS)
@pytest.mark.parametrize("centre", CENTRES)
def test_mirrored_and_degenerate_frames(pairs, centre):
    rng = np.random.default_rng(18)
    frame = rng.standard_normal((6, 3))
    mirrored = frame.copy()
    mirrored[:, 0] *= -1
    for left, right in {tuple(pair) for pair in pairs}:
        frame[right] = mirrored[left]
    _compare(frame, pairs, **centre)
    _compare(np.zeros((6, 3)), pairs, **centre)
    _compare(np.ones((6, 3)), pairs, **centre)


@pytest.mark.parametrize("bad", [np.nan, np.inf, -np.inf])
def test_non_finite_frames_are_invalid_input(bad):
    frame = np.random.default_rng(18).standard_normal((6, 3))
    frame[1, 1] = bad
    result = reflection(6, [(0, 1)]).process(frame)
    assert result.status == Status.INVALID_INPUT and result.reason


def test_pairs_are_sorted_labelled_and_deduplicated():
    pairs = [(3, 2), (0, 1), (3, 2)]
    new = reflection(4, pairs)
    assert new.outputs.flat_names == ("pair_symmetry_j0_j1", "pair_symmetry_j3_j2")  # the order of the reference, by name


def test_a_frame_of_another_size_than_the_labels_raises():
    with pytest.raises(ValueError, match="skeleton"):
        reflection(4, [(0, 1), (2, 3)]).process(np.zeros((3, 3)))


def test_constructor_validation():
    labels = ["a", "b", "c"]
    for bad in ([], "x", [("a", "b", "c")], [("a", "z")], [(0, 1)]):
        with pytest.raises((TypeError, ValueError)):
            Symmetry(method="reflection", labels=labels, pairs=bad)
    with pytest.raises(ValueError, match="labels"):
        Symmetry(method="reflection", labels=labels, pairs=[("a", "b")], reference_point="z")
    with pytest.raises(ValueError, match="pairs"):
        Symmetry(method="reflection", pairs=[("a", "b")])
