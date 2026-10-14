"""Parity of the core-backed PhaseLockingValue (PLV) with the preserved pure-Python/scipy reference
(tests/reference/phase_reference.py). Needs the compiled core: set EYESWEB_CORE_PATH (tests are skipped otherwise)."""
import json
import os
import sys

import numpy as np
import pytest

if os.environ.get("EYESWEB_CORE_PATH"):
    sys.path.insert(0, os.environ["EYESWEB_CORE_PATH"])
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "reference"))

pytest.importorskip("pyeyesweb._core", exc_type=ImportError)

from phase_reference import SynchronizationReference  # noqa: E402
from pyeyesweb.analysis_primitives.synchronization import PhaseLockingValue  # noqa: E402
from pyeyesweb.data_models import InputKind  # noqa: E402
from pyeyesweb.data_models.results import Status  # noqa: E402

FILTERS = [None, (1.0, 10.0, 100.0), (0.5, 4.0, 25.0), (5, 20, 100), (2.0, 30.0, 200.0)]


def _band(filter_params):
    """The `(low, high, rate)` of the reference's `filter_params` as the keywords of the feature."""
    return {} if filter_params is None else dict(zip(("low_frequency", "high_frequency", "sampling_rate"), filter_params))


def _new(window, filter_params):
    """The first two signals of a (T, signals, dims) window of the reference, as the two inputs of the feature."""
    flat = window.reshape(window.shape[0], -1)
    return PhaseLockingValue(window=max(len(window), 1), **_band(filter_params))._process_window(flat[:, 0], flat[:, 1])


def _compare(window, filter_params, tol=1e-9):
    new = _new(window, filter_params)
    ref = SynchronizationReference(filter_params=filter_params).compute(window)
    assert new.status == ref.status
    if ref.status == Status.OK:
        np.testing.assert_allclose(new["phase_locking_value"], ref["phase_locking_value"], rtol=0, atol=tol)
    return abs(new["phase_locking_value"] - ref["phase_locking_value"]) if ref.status == Status.OK else 0.0


@pytest.mark.parametrize("filter_params", FILTERS)
def test_random_windows(filter_params):
    rng = np.random.default_rng(1)
    worst = 0.0
    for length in (28, 29, 50, 100, 257, 1000):
        for _ in range(5):
            worst = max(worst, _compare(rng.standard_normal((length, 2, 1)), filter_params))
    print("max difference", worst)


@pytest.mark.parametrize("filter_params", FILTERS)
def test_coupled_signals(filter_params):
    rng = np.random.default_rng(2)
    times = np.arange(300) / 100.0
    first_signal = np.sin(2 * np.pi * 3 * times) + 0.2 * rng.standard_normal(300)
    second_signal = np.sin(2 * np.pi * 3 * times + 0.8) + 0.2 * rng.standard_normal(300)
    noise = rng.standard_normal(300)
    _compare(np.stack([first_signal, second_signal], axis=1)[:, :, None], filter_params)
    _compare(np.stack([first_signal, second_signal, noise, first_signal], axis=1).reshape(300, 2, 2), filter_params)  # the reference ignores the extra signals


@pytest.mark.parametrize("filter_params", FILTERS)
def test_degenerate_windows(filter_params):
    _compare(np.ones((60, 2, 1)), filter_params)
    _compare(np.zeros((60, 2, 1)), filter_params)
    signals = np.random.default_rng(3).standard_normal((60, 2, 1))
    signals[10, 0, 0] = np.nan
    new = _new(signals, filter_params)["phase_locking_value"]
    ref = SynchronizationReference(filter_params=filter_params).compute(signals)["phase_locking_value"]
    assert np.isnan(new) and np.isnan(ref)


def test_short_windows():
    for length in (1, 2, 5, 27):
        window = np.random.default_rng(4).standard_normal((length, 2, 1))
        _compare(window, None)
        with pytest.raises(ValueError):
            _new(window, (1.0, 10.0, 100.0))
        with pytest.raises(ValueError):
            SynchronizationReference(filter_params=(1.0, 10.0, 100.0)).compute(window)
    with pytest.raises(ValueError):
        SynchronizationReference().compute(np.zeros((0, 2, 1)))
    with pytest.raises(ValueError):
        PhaseLockingValue(window=1)._process_window(np.zeros((1, 0)), np.zeros((1, 0)))


@pytest.mark.parametrize("bad", [(10.0, 1.0, 100.0), (1.0, 60.0, 100.0), (1.0, 10.0, 0.0), (0.0, 10.0, 100.0)])
def test_invalid_filter_params(bad):
    with pytest.raises(ValueError):
        PhaseLockingValue(window=60, **_band(bad))


# ----------------------------------------------------------------------------------------------- two declared inputs

def test_two_declared_sample_inputs():
    feature = PhaseLockingValue(window=10)
    assert feature.inputs.names == ("first_signal", "second_signal")
    assert all(declared.kind is InputKind.SAMPLE and declared.shape == (1,) for declared in feature.inputs)


@pytest.mark.parametrize("arguments", [([1.0],), ([1.0], [2.0], [3.0]), ([1.0, 2.0], [3.0]), ([[1.0, 2.0]], [3.0])])
def test_wrong_number_of_arguments_or_non_scalar_sample_fails_at_the_first_call(arguments):
    with pytest.raises(ValueError):
        PhaseLockingValue(window=10).process(*arguments)


def test_run_takes_the_two_signals_and_equals_process():
    rng = np.random.default_rng(5)
    first_signal, second_signal = rng.standard_normal(60), rng.standard_normal(60)
    feature = PhaseLockingValue(window=20, hop=10)
    recording = feature.run(first_signal, second_signal, timestamps=np.arange(60) * 0.01)
    feature.reset()
    streamed = [feature.process(first, second, timestamp=index * 0.01) for index, (first, second) in enumerate(zip(first_signal, second_signal))]
    assert np.array_equal(recording["phase_locking_value"], [result["phase_locking_value"] for result in streamed], equal_nan=True)
    assert recording.status[19] == Status.OK and recording.status[20] == Status.NO_OUTPUT


# ----------------------------------------------------------------------------------------------- the frozen reference

FROZEN = os.path.join(os.path.dirname(__file__), "..", "data", "phase_locking_value_reference.npz")


def _frozen_cases():
    with np.load(FROZEN) as archive:
        meta = json.loads(str(archive["meta"]))
        return [pytest.param(entry, archive[f"case{index}"], id=entry["name"]) for index, entry in enumerate(meta)]


@pytest.mark.parametrize("entry,data", _frozen_cases())
def test_two_input_feature_reproduces_the_frozen_outputs_of_the_list_input_feature(entry, data):
    """Outputs, statuses and reasons that the former single-input (list of signals) feature gave on the same windows."""
    params = {name: tuple(value) if isinstance(value, list) else value for name, value in entry["params"].items()}
    feature = PhaseLockingValue(**params)
    if entry["kind"] != "window" and not np.isfinite(data).all():
        # the old feature buffered a NaN sample; now it is rejected and not buffered: the rest is the stream without it
        clean = PhaseLockingValue(**params)
        for step in range(data.shape[1]):
            result = feature.process(data[0, step], data[1, step], timestamp=entry["dt"] * (step + 1))
            if np.isfinite(data[:, step]).all():
                assert np.array_equal(result.to_array(), clean.process(data[0, step], data[1, step]).to_array(), equal_nan=True)
            else:
                assert result.status is Status.INVALID_INPUT and not any(result.valid.values())
        return
    if entry["kind"] == "window":
        results = [feature._process_window(data[:1], data[1:2])]
    else:
        results = [feature.process(data[0, step], data[1, step], timestamp=entry["dt"] * (step + 1)) for step in range(data.shape[1])]
    assert len(results) == len(entry["records"])
    for result, expected in zip(results, entry["records"]):
        assert (int(result.status), result.reason) == (expected["status"], expected["reason"])
        assert np.array_equal(result.timestamp, expected["timestamp"], equal_nan=True)
        assert np.array_equal(result["phase_locking_value"], expected["outputs"]["phase_locking_value"], equal_nan=True)
