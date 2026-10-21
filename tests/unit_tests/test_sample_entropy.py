"""SampleEntropy: the tolerance is `relative_tolerance * std(window)` unless `tolerance` is given.

An explicit `tolerance` gives exactly the numbers of the block before the relative default existed (frozen outputs,
tests/data/sample_entropy_reference.npz, made with the old core: bit for bit).
"""
import inspect
import json
import os
import sys
from pathlib import Path

import numpy as np
import pytest

if os.environ.get("EYESWEB_CORE_PATH"):
    sys.path.insert(0, os.environ["EYESWEB_CORE_PATH"])

pytest.importorskip("pyeyesweb._core", exc_type=ImportError)

from floats import assert_same_floats  # noqa: E402
from pyeyesweb.analysis_primitives import SampleEntropy  # noqa: E402
from pyeyesweb.data_models.results import Status  # noqa: E402

DATA = Path(__file__).resolve().parents[1] / "data"


def _frozen_cases():
    with np.load(DATA / "sample_entropy_reference.npz") as archive:
        meta = json.loads(str(archive["meta"]))
        return [pytest.param(entry, archive[f"signal{index}"], archive[f"entropy{index}"], id=entry["name"])
                for index, entry in enumerate(meta)]


def _speed_mm_per_s():
    """Speed of the right hand of a Qualisys excerpt (positions in mm, 100 Hz): values of the order of 100 to 1000."""
    with np.load(DATA / "motion_excerpts.npz") as archive:
        hand = archive["trial21"][:, list(archive["names"]).index("Right_Hand")]
    return np.linalg.norm(np.diff(hand, axis=0), axis=1) * 100.0


@pytest.mark.parametrize("entry,signal,expected", _frozen_cases())
def test_explicit_tolerance_gives_the_numbers_of_the_old_default_bit_for_bit(entry, signal, expected):
    feature = SampleEntropy(window=len(signal), embedding_dimension=entry["embedding_dimension"], tolerance=entry["tolerance"])
    assert_same_floats(feature._process_window(signal)["sample_entropy"], expected)


def test_the_tolerance_defaults_to_none_and_relative_tolerance_to_0_2():
    parameters = inspect.signature(SampleEntropy).parameters
    assert parameters["tolerance"].default is None and parameters["relative_tolerance"].default == 0.2
    feature = SampleEntropy(window=40)
    assert feature.tolerance is None and feature.relative_tolerance == 0.2


def test_none_means_relative_tolerance_times_the_population_std_of_the_window():
    signal = np.sin(np.arange(120) / 4.0) + 0.2 * np.random.default_rng(3).standard_normal(120)
    relative = SampleEntropy(window=120, embedding_dimension=4)._process_window(signal)["sample_entropy"]
    explicit = SampleEntropy(window=120, embedding_dimension=4, tolerance=0.2 * np.std(signal))._process_window(signal)["sample_entropy"]
    assert np.allclose(relative, explicit, rtol=0, atol=1e-12)
    half = SampleEntropy(window=120, embedding_dimension=4, relative_tolerance=0.5)._process_window(signal)["sample_entropy"]
    assert not np.allclose(half, relative)
    assert np.allclose(half, SampleEntropy(window=120, embedding_dimension=4, tolerance=0.5 * np.std(signal))._process_window(signal)["sample_entropy"], atol=1e-12)


def test_the_default_is_independent_of_the_scale_of_the_signal():
    signal = np.cumsum(np.random.default_rng(5).standard_normal(150))
    small = SampleEntropy(window=150, embedding_dimension=3)._process_window(signal)["sample_entropy"]
    large = SampleEntropy(window=150, embedding_dimension=3)._process_window(1000.0 * signal + 7.0)["sample_entropy"]
    assert np.allclose(small, large, atol=1e-9)


def test_a_real_speed_window_in_mm_per_s_is_finite_by_default_and_inf_with_the_old_absolute_tolerance():
    window = _speed_mm_per_s()[:300]
    assert window.std() > 50  # mm/s: a tolerance of 0.3 is far below the scale of the signal
    default = SampleEntropy(window=300, embedding_dimension=12)._process_window(window)
    assert default.status is Status.OK and np.isfinite(default["sample_entropy"]).all()
    old_default = SampleEntropy(window=300, embedding_dimension=12, tolerance=0.3)._process_window(window)
    assert not np.isfinite(old_default["sample_entropy"]).all()  # what the block gave before: A[k] = 0 -> inf


def test_a_constant_window_uses_a_tiny_tolerance_and_does_not_divide_by_zero():
    result = SampleEntropy(window=20, embedding_dimension=3)._process_window(np.full(20, 5.0))
    assert result.status is Status.OK and np.isfinite(result["sample_entropy"]).all()
    assert result["sample_entropy"][0] == 0.0


def test_tolerance_and_relative_tolerance_are_live_and_validated():
    signal = np.random.default_rng(9).standard_normal(60)
    feature = SampleEntropy(window=60, embedding_dimension=2)
    first = feature._process_window(signal)["sample_entropy"].copy()
    feature.tolerance = 0.5
    assert np.array_equal(feature._process_window(signal)["sample_entropy"],
                          SampleEntropy(window=60, embedding_dimension=2, tolerance=0.5)._process_window(signal)["sample_entropy"])
    feature.tolerance = None
    assert np.array_equal(feature._process_window(signal)["sample_entropy"], first)
    feature.relative_tolerance = 0.5
    assert np.array_equal(feature._process_window(signal)["sample_entropy"],
                          SampleEntropy(window=60, embedding_dimension=2, relative_tolerance=0.5)._process_window(signal)["sample_entropy"])
    with pytest.raises(ValueError):
        feature.relative_tolerance = 0.0
    assert feature.relative_tolerance == 0.5
