"""Catalog-wide invariants of the status contract (`DEVELOPMENT_SPEC.md` section 3), on valid data and on data with a NaN
burst, an infinity and a huge value (1e300), for every feature of `catalog()`.

For every call of every feature:

* it never raises (the recordings have the declared shapes: `ValueError` is only for a wrong shape);
* `status == OK` implies that every valid float output is finite (`EXCEPTIONS` lists a feature that does not, with the reason);
* `status == INVALID_INPUT` implies that every output holds its empty value (NaN, 0, False) and `valid` is `False` for all;
* a sample rejected for NaN or infinity is not buffered and advances nothing: the results of the other samples equal those of
  a run that never saw it.

The recordings come from `test_contract_all_features` (its `OVERRIDES` table and `from_inputs`), so a new catalog feature is
driven here as it is there. Images have no finite check and are only run unperturbed.
"""

import numpy as np
import pytest

pytest.importorskip("pyeyesweb._core", exc_type=ImportError)

from test_contract_all_features import NAMES, factory_and_recordings  # noqa: E402

from pyeyesweb.data_models import InputKind, Status  # noqa: E402

# name -> why an OK result may hold a non-finite valid output
EXCEPTIONS = {
    "EnsembleDominance": "a NaN complexity index marks a participant without one (a constant signal): it is ignored and "
                         "its dominance score is NaN by design (the input opts out of the finite check)",
}

CORRUPTIONS = {
    "nan_burst": lambda recording: _set(recording, slice(len(recording) // 4, len(recording) // 4 + 3), np.nan),
    "infinity": lambda recording: _set(recording, len(recording) // 2, np.inf, first_value_only=True),
    "huge": lambda recording: _set(recording, 3 * len(recording) // 4, 1e300),
}


def _set(recording, where, value, first_value_only=False):
    corrupted = np.array(recording, dtype=float)
    if first_value_only:
        corrupted[(where,) + (0,) * (corrupted.ndim - 1)] = value
    else:
        corrupted[where] = value
    return corrupted


def _run(factory, recordings, skip=()):
    """The results of a fresh feature on the frames not in `skip`, with the index of each frame."""
    feature = factory()
    return [(index, feature.process(*(recording[index] for recording in recordings)))
            for index in range(len(recordings[0])) if index not in skip]


def _empty(result):
    for output in result.schema:
        value = result[output.name]
        for item in (value.values() if output.labelled else [value]):
            array = np.asarray(item)
            assert (np.isnan(array).all() if output.kind is float else not array.any()), (output.name, value)
    assert not any(result.valid.values())


def _finite_when_valid(result):
    for output in result.schema:
        if output.kind is float and result.valid[output.name]:
            value = result[output.name]
            for item in (value.values() if output.labelled else [value]):
                assert np.isfinite(np.asarray(item)).all(), (output.name, value)


def _same(first, second):
    return first.status == second.status and first == second


@pytest.mark.parametrize("corruption", [None, *CORRUPTIONS])
@pytest.mark.parametrize("name", NAMES)
def test_status_invariants(name, corruption):
    factory, recordings = factory_and_recordings(name)
    images = any(declared.kind is InputKind.IMAGE for declared in factory().inputs)
    if corruption is not None:
        if images:
            pytest.skip("images have no finite check")
        recordings = tuple(CORRUPTIONS[corruption](recording) for recording in recordings)
    results = _run(factory, recordings)
    for index, result in results:
        if result.status is Status.OK and name not in EXCEPTIONS:
            _finite_when_valid(result)
        if result.status is Status.INVALID_INPUT:
            _empty(result)
    if corruption in ("nan_burst", "infinity"):
        rejected = {index for index, result in results if result.status is Status.INVALID_INPUT
                    and not all(np.isfinite(recording[index]).all() for recording in recordings)}
        if rejected:  # the rejected samples were not buffered and advanced no state
            for (index, result), (clean_index, clean) in zip([item for item in results if item[0] not in rejected],
                                                             _run(factory, recordings, skip=rejected)):
                assert index == clean_index and _same(result, clean), (name, index)



def test_a_rejected_sample_moves_no_counter_under_live_window_and_hop_changes():
    """The hop counter and `latest` only advance on accepted samples, also when `window` and `hop` change live."""
    from pyeyesweb.low_level import SpectralArcLength
    signal = np.abs(np.sin(np.arange(120) / 7.0)) + 0.5
    seen_nan, never_saw_it = SpectralArcLength(window=20, hop=5, sampling_rate=50.0), SpectralArcLength(window=20, hop=5, sampling_rate=50.0)
    accepted = 0
    for index, value in enumerate(signal):
        if index in (7, 33, 34, 61):
            assert seen_nan.process(np.nan).status is Status.INVALID_INPUT
        if accepted == 30:
            seen_nan.configure(window=16, hop=3)
            never_saw_it.configure(window=16, hop=3)
        if accepted == 70:
            seen_nan.hop = never_saw_it.hop = 7
        result, expected = seen_nan.process(value), never_saw_it.process(value)
        accepted += 1
        assert _same(result, expected)
        assert (seen_nan.latest is None) == (never_saw_it.latest is None) and (seen_nan.latest is None or _same(seen_nan.latest, never_saw_it.latest))
    assert accepted == len(signal)


def test_points_with_a_nan_are_rejected_as_arrays_and_as_dicts():
    from pyeyesweb.low_level import KineticEnergy, PointsDensity
    energy = KineticEnergy(labels=["a", "b"], weights={"a": 1.0, "b": 1.0})
    assert energy.process(np.array([[0.0, 0, 0], [1, 1, 1]])).ok
    for frame in (np.array([[np.nan, 0, 0], [1, 1, 1]]), {"a": (0.0, np.inf, 0.0), "b": (1.0, 1.0, 1.0)}):
        result = energy.process(frame)
        assert result.status is Status.INVALID_INPUT and result.reason == "NaN or infinite values" and not any(result.valid.values())
    density = PointsDensity()
    assert density.process(np.array([[0.0, 0, 0], [1, np.nan, 1]])).status is Status.INVALID_INPUT
    assert density.process(np.array([[0.0, 0, 0], [1, 1, 1]])).ok
