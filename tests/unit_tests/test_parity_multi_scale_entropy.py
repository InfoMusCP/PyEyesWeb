"""Parity of MultiScaleEntropy and EnsembleDominance (C++ core) with the pure-Python 1.x implementation, and with the
frozen outputs of the combined MultiScaleEntropyDominance block they replace.

The reference is a verbatim copy of the 1.x module (tests/reference/mse_dominance_reference.py). The core composes the
EyesWeb CoarseGraining and SampleEntropy blocks, which count templates slightly differently from the original
(see multi_scale_entropy.h), so entropies agree to O(1/N), not to rounding: the tolerance is `TOL`.
Everything that does not depend on the template counts (coarse graining, degenerate cases, trapezoid, dominance,
leader, NaN quirks, statuses) is checked exactly.

The compiled core is found as pyeyesweb._eyesweb_core, or as eyesweb_core in the directory named by the
EYESWEB_CORE_PATH environment variable. Without it these tests are skipped.
"""
import importlib.util
import json
import math
import os
import sys
from pathlib import Path

import numpy as np
import pytest

if os.environ.get("EYESWEB_CORE_PATH"):
    sys.path.insert(0, os.environ["EYESWEB_CORE_PATH"])

core_module = pytest.importorskip("pyeyesweb._core", exc_type=ImportError)

from pyeyesweb.analysis_primitives import MultiScaleEntropy
from pyeyesweb.high_level import EnsembleDominance  # noqa: E402
from pyeyesweb.data_models.results import Status  # noqa: E402

TOL = 0.05  # entropy difference allowed between the reference and the core, N around 300-1500

REFERENCE_FILE = Path(__file__).resolve().parents[1] / "reference" / "mse_dominance_reference.py"


def _load_reference():
    spec = importlib.util.spec_from_file_location("mse_dominance_reference", REFERENCE_FILE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.MultiScaleEntropyDominance


Reference = _load_reference()


@pytest.fixture(autouse=True)
def numpy_trapz(monkeypatch):
    """The 1.x reference calls np.trapz, which NumPy 2 renamed."""
    if not hasattr(np, "trapz"):
        monkeypatch.setattr(np, "trapz", np.trapezoid, raising=False)


class _Window2D:
    """The window interface the 1.x reference reads (`is_full`, `to_array(as2D=True)`)."""

    def __init__(self, data):
        self._data = data

    def is_full(self):
        return True

    def to_array(self, as2D=True):
        return self._data, None


def reference_call(data, **params):
    return Reference(**params)(_Window2D(data))


def make(window=None, **params):
    window = window or params.get("max_scale", 6) * params.get("minimum_points", 500)
    return MultiScaleEntropy(window=window, **params)


def reference_params(params):
    """The 1.x names of the parameters (`min_points` was renamed `minimum_points`)."""
    return {("min_points" if name == "minimum_points" else name): value for name, value in params.items()}


def compute(feature, data):
    """One window of `data` ((Time,) or (Time, signals)) through `_process_window`, which takes (signals, Time)."""
    return feature._process_window(np.asarray(data, dtype=float).T)


def noise(count, seed, signals=1):
    return np.random.default_rng(seed).standard_normal((count, signals))


# ----------------------------------------------------------------------------------------------- the maths

@pytest.mark.parametrize("seed", range(4))
@pytest.mark.parametrize("embedding_dimension,tolerance", [(1, 0.2), (2, 0.15), (3, 0.3)])
def test_sample_entropy_close_to_reference(seed, embedding_dimension, tolerance):
    signal = noise(600, seed)[:, 0]
    ref = Reference(embedding_dimension=embedding_dimension, tolerance=tolerance)
    core = make(embedding_dimension=embedding_dimension, tolerance=tolerance)._block
    assert core.sample_entropy(signal) == pytest.approx(ref._sample_entropy(signal), abs=TOL)


def test_sample_entropy_degenerate_cases_exact():
    ref, core = Reference(embedding_dimension=2), make(embedding_dimension=2)._block
    for signal in (np.full(100, 3.0), noise(12, 0)[:, 0], np.zeros(500)):
        reference_value, core_value = ref._sample_entropy(signal), core.sample_entropy(signal)
        assert (math.isnan(reference_value) and math.isnan(core_value)) or reference_value == core_value


@pytest.mark.parametrize("seed", range(3))
@pytest.mark.parametrize("params", [dict(max_scale=1, minimum_points=100), dict(max_scale=4, minimum_points=150),
                                    dict(max_scale=6, minimum_points=500), dict(max_scale=3, minimum_points=50, embedding_dimension=3)])
def test_complexity_index_close_to_reference(seed, params):
    signal = noise(1200, seed)[:, 0]
    ref = Reference(**reference_params(params))._calculate_complexity_index(signal)
    assert make(**params)._block.complexity_index(signal) == pytest.approx(ref, abs=TOL * params["max_scale"])


def test_complexity_index_scales_stop_at_minimum_points():
    signal = noise(1000, 1)[:, 0]
    # 1000 / 2 = 500 >= 500 but 1000 / 3 < 500: two scales in both implementations
    assert make(max_scale=6)._block.complexity_index(signal) == pytest.approx(
        Reference(max_scale=6)._calculate_complexity_index(signal), abs=2 * TOL)


# ----------------------------------------------------------------------------------------------- the features

def test_matches_reference_dict_for_several_signals():
    data = np.column_stack([noise(600, 1)[:, 0], np.sin(np.arange(600) / 9.0), noise(600, 2)[:, 0] * 2 + 5])
    params = dict(max_scale=2, minimum_points=250)
    ref = reference_call(data, **reference_params(params), methods=["complexity_index", "dominance_score", "leader_identification"])
    entropy = compute(make(**params), data)
    dominance = EnsembleDominance().process(entropy.complexity_index)

    assert entropy.status is Status.OK and dominance.status is Status.OK
    np.testing.assert_allclose(entropy.complexity_index, ref["complexity_index"], atol=2 * TOL)
    np.testing.assert_allclose(dominance.dominance_score, ref["dominance_score"], atol=0.1)
    assert dominance.leader_index == ref["leader_complexity"][0] == 1  # the sine is the most regular
    assert dominance.leader_complexity == pytest.approx(ref["leader_complexity"][1], abs=2 * TOL)
    assert dominance.dominance_score[dominance.leader_index] == pytest.approx(
        1 - dominance.leader_complexity / entropy.complexity_index.max())


def test_scale_entropies_are_the_curve_of_the_complexity_index():
    data = np.column_stack([noise(450, 8)[:, 0], np.sin(np.arange(450) / 5.0)])
    result = compute(make(max_scale=3, minimum_points=150), data)
    assert result.scale_entropies.shape == (2, 3)
    trapezoid = (result.scale_entropies[:, :-1] + result.scale_entropies[:, 1:]).sum(axis=1) / 2
    np.testing.assert_allclose(trapezoid, result.complexity_index, rtol=1e-14)


def test_scales_below_the_minimum_points_are_nan():
    feature = make(window=200, max_scale=4, minimum_points=50)  # 200 / 4 = 50: every scale is used
    assert np.isfinite(feature._process_window(noise(200, 9).T).scale_entropies).all()
    short = MultiScaleEntropy(window=200, max_scale=2, minimum_points=100)
    result = short._process_window(noise(300, 9).T[:, :199])  # scale 2 has 99 points
    assert np.isfinite(result.scale_entropies[0, 0]) and np.isnan(result.scale_entropies[0, 1])


def test_single_signal_is_an_array_not_a_scalar():
    data = noise(500, 3)
    ref = reference_call(data)
    result = compute(make(), data)
    assert isinstance(ref["complexity_index"], float)
    assert result.complexity_index.shape == (1,)
    assert result.complexity_index[0] == pytest.approx(ref["complexity_index"], abs=TOL)
    np.testing.assert_array_equal(compute(make(), data[:, 0]).complexity_index, result.complexity_index)


def test_nan_signals_are_ignored_by_the_dominance_unlike_the_reference():
    data = np.column_stack([noise(500, 4)[:, 0], np.ones(500)])
    ref = reference_call(data, methods=["dominance_score", "leader_identification"])
    assert ref["dominance_score"] == [0.0, 0.0] and ref["leader_complexity"][0] == 1  # the 1.x quirk
    complexity_index = compute(make(), data).complexity_index
    assert math.isnan(complexity_index[1])
    result = EnsembleDominance().process(complexity_index)
    assert result.leader_index == 0 and math.isnan(result.dominance_score[1])


def test_input_too_short_is_warming_up_and_matches_reference_nan():
    data = noise(499, 5)
    assert math.isnan(reference_call(data)["complexity_index"])
    result = compute(make(), data)
    assert result.status is Status.WARMING_UP and not result.valid["complexity_index"]
    assert result.complexity_index.size == 0


@pytest.mark.parametrize("bad", [np.array([]), np.array([1.0, np.nan] * 300), np.full(600, np.inf)])
def test_invalid_input(bad):
    result = compute(make(), bad)
    assert result.status is Status.INVALID_INPUT and result.reason


def test_streaming_and_warming_up():
    feature = make(max_scale=1, minimum_points=100)
    rng = np.random.default_rng(6)
    results = [feature.process(rng.standard_normal(2), timestamp=index * 0.01) for index in range(100)]
    assert all(outcome.status is Status.WARMING_UP for outcome in results[:99])
    result = results[99]
    assert result.status is Status.OK and result.complexity_index.shape == (2,) and result.timestamp == pytest.approx(0.99)
    assert np.isfinite(result.complexity_index).all()


def test_schemas_and_parameters_are_validated():
    assert make().outputs.names == ("complexity_index", "scale_entropies")
    assert make(max_scale=3, window=3000).outputs["scale_entropies"].shape == (None, 3)
    assert EnsembleDominance().outputs.names == ("dominance_score", "leader_index", "leader_complexity")
    assert EnsembleDominance().outputs["leader_index"].kind is int
    for bad in (dict(embedding_dimension=0), dict(tolerance=1.0), dict(max_scale=0), dict(minimum_points=0)):
        with pytest.raises(Exception):
            make(**bad)


def test_parameter_change_reaches_the_core():
    feature = make(max_scale=1, window=1000)
    data = noise(1000, 7)
    one = compute(feature, data).complexity_index[0]
    feature.max_scale = 2
    assert compute(feature, data).complexity_index[0] != one
    assert feature.outputs["scale_entropies"].shape == (None, 2)


def test_ensemble_dominance_inputs_and_infinite_index():
    dominance = EnsembleDominance()
    assert dominance.inputs["complexity_index"].shape == (None,)
    result = dominance.process([4.0, 1.0, 2.0])
    np.testing.assert_array_equal(result.dominance_score, [0.0, 0.75, 0.5])
    assert result.leader_index == 1 and result.leader_complexity == 1.0
    assert dominance.process([1.0, np.inf]).status is Status.INVALID_INPUT
    assert np.array_equal(dominance.run(np.array([[4.0, 1.0], [2.0, 8.0]]))["leader_index"], [1, 0])


# ----------------------------------------------------------------------------------------------- the frozen reference

FROZEN = Path(__file__).resolve().parents[1] / "data" / "multi_scale_entropy_reference.npz"


def _frozen_cases():
    with np.load(FROZEN) as archive:
        meta = json.loads(str(archive["meta"]))
        return [pytest.param(entry, archive[f"case{index}"], id=entry["name"]) for index, entry in enumerate(meta)]


def _equal(actual, expected):
    return np.array_equal(np.asarray(actual, dtype=float), np.asarray(expected, dtype=float), equal_nan=True)


@pytest.mark.parametrize("entry,data", _frozen_cases())
def test_split_reproduces_the_combined_block_bit_for_bit(entry, data):
    """`MultiScaleEntropy` then `EnsembleDominance` give the outputs, statuses and reasons that the frozen
    MultiScaleEntropyDominance (all three methods) gave on the same windows."""
    params = {("minimum_points" if name == "min_points" else name): value for name, value in entry["params"].items() if name != "methods"}
    feature, dominance = MultiScaleEntropy(**params), EnsembleDominance()
    if entry["kind"] != "window" and not np.isfinite(data).all():
        # the old block buffered a NaN sample; now it is rejected and not buffered: the rest is the stream without it
        clean = MultiScaleEntropy(**params)
        for step in range(data.shape[1]):
            result = feature.process(data[:, step], timestamp=entry["dt"] * (step + 1))
            if np.isfinite(data[:, step]).all():
                assert np.array_equal(result.to_array(), clean.process(data[:, step]).to_array(), equal_nan=True)
            else:
                assert result.status is Status.INVALID_INPUT and not any(result.valid.values())
        return
    if entry["kind"] == "window":
        results = [feature._process_window(data)]
    else:
        results = [feature.process(data[:, step], timestamp=entry["dt"] * (step + 1)) for step in range(data.shape[1])]
    assert len(results) == len(entry["records"])
    for result, expected in zip(results, entry["records"]):
        assert (int(result.status), result.reason) == (expected["status"], expected["reason"])
        assert _equal(result.timestamp, expected["timestamp"])
        outputs = expected["outputs"]
        assert _equal(result.complexity_index, outputs["complexity_index"])
        if result.status is Status.OK:
            composed = dominance.process(result.complexity_index)
            assert _equal(composed.dominance_score, outputs["dominance_score"])
            assert composed.leader_index == outputs["leader_index"]
            assert _equal(composed.leader_complexity, outputs["leader_complexity"])
        else:
            assert outputs["dominance_score"] == []
