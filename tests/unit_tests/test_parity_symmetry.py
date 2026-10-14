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


_NEW_NAME = {"pair_error": "pair_symmetry"}  # the reference keeps the legacy output name


def _compare(frame, pairs, tol=1e-9, **params):
    new = Symmetry(method="reflection", joint_pairs=pairs, **params).process(frame)
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
    result = Symmetry(method="reflection", joint_pairs=[(0, 1)]).process(frame)
    assert result.status == Status.INVALID_INPUT and result.reason


def test_pairs_are_sorted_labelled_and_deduplicated():
    pairs = [(3, 2), (0, 1), (3, 2)]
    new, ref = Symmetry(method="reflection", joint_pairs=pairs), GeometricSymmetryReference(pairs)
    assert new.outputs.flat_names == tuple(name.replace("pair_error", "pair_symmetry") for name in ref.outputs.flat_names)
    assert "pair_symmetry_0_1" in new.outputs.flat_names and "pair_symmetry_3_2" in new.outputs.flat_names
    assert len(new.outputs.flat_names) == 2


def test_too_few_joints_is_invalid_input():
    assert _compare(np.zeros((3, 3)), [(0, 1), (2, 3)]).status == Status.INVALID_INPUT
    assert _compare(np.zeros((6, 3)), [(0, 1)], center_of_symmetry=6).status == Status.INVALID_INPUT


def test_constructor_validation_matches_the_reference():
    for bad in ([], "x", [(0, 1, 2)], [(0, 1.5)]):
        with pytest.raises((TypeError, ValueError)) as new:
            Symmetry(method="reflection", joint_pairs=bad)
        with pytest.raises((TypeError, ValueError)) as ref:
            GeometricSymmetryReference(bad)
        assert type(new.value) is type(ref.value)
