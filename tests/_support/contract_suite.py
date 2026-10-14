"""One reusable check of the call contract (`Feature`), used by the tests of every migrated feature.

    from contract_suite import check_feature_contract
    check_feature_contract(lambda: Periodicity(window=64, hop=16), signal)         # one input
    check_feature_contract(lambda: CrossRecurrencePlot(window=32), x, y)           # two inputs

`factory` builds a fresh feature, `data` is one recording per input (time on the first axis). The checks are the
rules of docs/user_guide/input_contract.md and docs/user_guide/output_contracts.md.
"""

import math

import numpy as np
import pytest

from pyeyesweb.data_models import Feature, Recorder, Result


def _equal(left, right):
    """Outputs are equal when every number is: arrays (NaN equal), dicts of arrays (labelled outputs), lists."""
    if isinstance(left, dict) or isinstance(right, dict):
        return isinstance(left, dict) and isinstance(right, dict) and left.keys() == right.keys() and all(
            _equal(left[key], right[key]) for key in left)
    if isinstance(left, (list, tuple)) and isinstance(right, (list, tuple)):
        return len(left) == len(right) and all(_equal(left_item, right_item) for left_item, right_item in zip(left, right))
    try:
        left_array, right_array = np.asarray(left), np.asarray(right)
        return left_array.shape == right_array.shape and np.array_equal(left_array, right_array, equal_nan=left_array.dtype.kind in "fc" and right_array.dtype.kind in "fc")
    except TypeError:
        return left == right


def _assert_rows_equal(rec_a, rec_b, what):
    assert len(rec_a) == len(rec_b), what
    assert np.array_equal(rec_a.status, rec_b.status), what
    for name in rec_a.schema.names:
        column_a, column_b = rec_a[name], rec_b[name]
        for index in range(len(rec_a)):
            assert _equal(column_a[index], column_b[index]), (what, name, index)


def check_feature_contract(factory, *data, timestamps=True, chunking=True):
    """Assert that the feature built by `factory` obeys the call contract on the recording `data`."""
    arrays = [np.asarray(part, dtype=float) for part in data]
    row_count = len(arrays[0])

    feature = factory()
    assert isinstance(feature, Feature), "features derive from Feature"
    assert len(feature.inputs) == len(arrays), "one recording per declared input"
    assert feature.inputs.describe() and len(feature.outputs) >= 1

    # process and run agree, row by row
    streaming = factory()
    results = [streaming.process(*(array[position] for array in arrays)) for position in range(row_count)]
    assert all(isinstance(outcome, Result) for outcome in results)
    for result in results:
        assert result.schema.names == feature.outputs.names
        assert math.isnan(result.timestamp)
        result.to_array()
        with pytest.raises((AttributeError, TypeError)):
            result.status = 0
    recorded = factory().run(*arrays)
    assert isinstance(recorded, Recorder) and len(recorded) == row_count
    assert np.array_equal(recorded.status, [int(outcome.status) for outcome in results])
    for name in recorded.schema.names:
        for index, result in enumerate(results):
            assert _equal(result[name], recorded[name][index]), (name, index)

    # run starts fresh by default: it is a pure function of the recording
    again = feature.run(*arrays)
    first = feature.run(*arrays)
    _assert_rows_equal(first, again, "run twice")

    # reset=False continues; chunks add up to the whole recording
    if chunking and row_count >= 4:
        half = row_count // 2
        chunked = factory()
        first_half = chunked.run(*(array[:half] for array in arrays))
        second_half = chunked.run(*(array[half:] for array in arrays), reset=False)
        assert np.array_equal(np.concatenate([first_half.status, second_half.status]), recorded.status), "chunked run"

    # latest is the last result with status OK (None before the first one), and reset forgets it
    held = factory()
    assert held.latest is None
    last_ok = None
    for position in range(row_count):
        outcome = held.process(*(array[position] for array in arrays))
        last_ok = outcome if outcome.ok else last_ok
        assert held.latest is last_ok, "latest"
    held.reset()
    assert held.latest is None, "latest after reset"

    # reset restarts the state
    head_length = min(row_count, 20)
    stream = factory()
    head = [stream.process(*(array[position] for array in arrays)).status for position in range(head_length)]
    stream.reset()
    assert [stream.process(*(array[position] for array in arrays)).status for position in range(head_length)] == head, "reset"

    # time: seconds, optional, validated
    if timestamps:
        ts = np.arange(row_count) * 0.02
        timed = factory().run(*arrays, timestamps=ts)
        ok = timed.ok
        assert np.allclose(timed.timestamps[ok], ts[ok]) and np.isnan(recorded.timestamps).all()
        with pytest.raises(ValueError):
            factory().run(*arrays, timestamps=ts[:-1])

    # wrong number of inputs
    with pytest.raises((ValueError, TypeError)):
        factory().run(*arrays, arrays[0])

    # a mis-shaped sample is a programming error: it raises, in `process` and before `run` loops
    check_input_validation(factory, *arrays)


def _wrong_samples(declared):
    """Samples that cannot fit the declared input: the wrong channel count, rank, dimension or number of points."""
    from pyeyesweb.data_models import InputKind
    wrong = []
    size, dims = (declared.shape + (None, None))[:2] if declared.kind is not InputKind.SAMPLE else (declared.shape[0], None)
    if declared.labels is not None and declared.shape[0] is None:
        size = len(declared.labels)
    if declared.kind is InputKind.SAMPLE:
        if size is not None:
            wrong += [np.ones(size + 1), np.ones((size, 2))]
    else:
        wrong.append(np.ones(3))                               # a flat vector is not a frame
        wrong.append(np.ones((2, 2, 2)))                       # nor a stack of frames
        if dims is not None:
            wrong.append(np.ones((size or 3, dims + 1)))
        if size is not None:
            wrong.append(np.ones((size + 1, dims or 3)))
    return wrong


def check_input_validation(factory, *data):
    """A sample whose shape does not fit a declared input raises `ValueError` naming the feature and the input."""
    arrays = [np.asarray(part, dtype=float) for part in data]
    for input_index, declared in enumerate(factory().inputs):
        for bad in _wrong_samples(declared):
            feature = factory()
            sample = [array[0] for array in arrays]
            sample[input_index] = bad
            with pytest.raises(ValueError, match=type(feature).__name__) as error:
                feature.process(*sample)
            assert declared.name in str(error.value)
