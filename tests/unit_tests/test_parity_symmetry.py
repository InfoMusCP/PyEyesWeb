"""Core-backed Symmetry (REFLECTION): input rules and labels. Needs the compiled core: set EYESWEB_CORE_PATH (tests are skipped
otherwise)."""
import os
import sys

import numpy as np
import pytest

if os.environ.get("EYESWEB_CORE_PATH"):
    sys.path.insert(0, os.environ["EYESWEB_CORE_PATH"])

pytest.importorskip("pyeyesweb._core", exc_type=ImportError)

from pyeyesweb.data_models.results import Status  # noqa: E402
from pyeyesweb.low_level.symmetry import Symmetry  # noqa: E402
from symmetry_inputs import reflection  # noqa: E402


@pytest.mark.parametrize("bad", [np.nan, np.inf, -np.inf])
def test_non_finite_frames_are_invalid_input(bad):
    frame = np.random.default_rng(18).standard_normal((6, 3))
    frame[1, 1] = bad
    result = reflection(6, [(0, 1)]).process(frame)
    assert result.status == Status.INVALID_INPUT and result.reason


def test_pairs_are_sorted_labelled_and_deduplicated():
    pairs = [(3, 2), (0, 1), (3, 2)]
    new = reflection(4, pairs)
    assert new.outputs.flat_names == ("pair_symmetry_j0_j1", "pair_symmetry_j3_j2")  # sorted, by name


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
