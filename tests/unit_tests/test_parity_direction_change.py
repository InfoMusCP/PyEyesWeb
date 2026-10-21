"""DirectionChange: window-level behaviour and the frozen outputs of the earlier signals form. Needs the compiled core:
set EYESWEB_CORE_PATH (tests are skipped otherwise)."""
import os
import sys

import numpy as np
import pytest

if os.environ.get("EYESWEB_CORE_PATH"):
    sys.path.insert(0, os.environ["EYESWEB_CORE_PATH"])

pytest.importorskip("pyeyesweb._core", exc_type=ImportError)

from floats import assert_same_floats  # noqa: E402
from pyeyesweb.data_models.results import Status  # noqa: E402
from pyeyesweb.low_level.direction_change import DirectionChange  # noqa: E402

METRIC_SETS = [None, ["cosine"], ["polygon"], ["polygon", "cosine"]]


def _new(window, **params):
    """The feature on a `(frames, signals, dims)` window: its `(dims, frames)` series is the mean over the signals."""
    feature = DirectionChange(window=max(len(window), 3), **params)
    return feature, feature._process_window(window.mean(axis=1).T)


@pytest.mark.parametrize("metrics", METRIC_SETS)
def test_non_finite_windows_are_invalid_input(metrics):
    window = np.random.default_rng(9).standard_normal((9, 2, 2))
    for index, bad in (((4, 0, 1), np.nan), ((0, 0, 0), np.inf)):
        window[index] = bad
        assert _new(window, metrics=metrics)[1].status == Status.INVALID_INPUT


@pytest.mark.parametrize("metrics", METRIC_SETS)
def test_short_windows_warm_up(metrics):
    for length in (0, 1, 2):
        assert _new(np.zeros((length, 1, 2)), metrics=metrics)[1].status == Status.WARMING_UP


def test_unsupported_dimensions_are_invalid_input():
    rng = np.random.default_rng(10)
    assert _new(rng.standard_normal((6, 2, 1)), metrics=["cosine"])[1].status == Status.INVALID_INPUT
    assert _new(rng.standard_normal((6, 2, 1)), metrics=["polygon"])[1].status == Status.INVALID_INPUT
    assert _new(rng.standard_normal((6, 2, 4)), metrics=["polygon"])[1].status == Status.INVALID_INPUT


def test_negative_num_subsamples_is_invalid_input():
    window = np.random.default_rng(11).standard_normal((8, 1, 2))
    assert _new(window, metrics=["polygon"], number_of_subsamples=-1)[1].status == Status.INVALID_INPUT


# ------------------------------------------------- one point per frame: the mean over the markers is the user's job
REFERENCE = os.path.join(os.path.dirname(__file__), "..", "data", "direction_change_reference.npz")
PARAMETER_SETS = [dict(window=20, hop=1), dict(window=30, hop=7), dict(window=3, hop=1),
                  dict(window=50, hop=50, epsilon=0.2, number_of_subsamples=7), dict(window=25, hop=5, metrics=["cosine"]),
                  dict(window=25, hop=5, metrics=["polygon"], number_of_subsamples=1000),
                  dict(window=12, hop=4, epsilon=1e-3, number_of_subsamples=3)]


def _recordings():
    """`(frames, signals, dims)` recordings, deterministic."""
    rng = np.random.default_rng(5)
    out = {f"rand/{signals}": np.cumsum(rng.normal(size=(120, signals, 3)) * 10, axis=0)
           + rng.normal(size=(120, signals, 3)) * 1000 for signals in (1, 2, 5, 8, 9, 13, 20)}
    out["neg0"] = np.zeros((30, 1, 3)) * -1.0
    out["still"] = np.ones((40, 2, 3))
    out["line"] = np.cumsum(np.ones((40, 1, 3)), axis=0)
    nan = out["rand/5"].copy()
    nan[50, 2, 1] = np.nan
    out["nan"] = nan
    infinite = out["rand/2"].copy()
    infinite[30, 0, 0], infinite[30, 1, 0] = np.inf, -np.inf
    out["infinity_minus_infinity"] = infinite
    with np.errstate(over="ignore"):
        out["overflow"] = out["rand/2"] * 1e307
    out["rand/fortran"] = np.asfortranarray(out["rand/20"])
    return out


def _bits(values):
    return np.asarray(values, dtype=float).view(np.int64)


def _frame(recorder):
    """`to_frame()` with the status codes of the frozen file in place of the names (and without the reasons, it has none)."""
    return recorder.to_frame().drop(columns="reason").replace({"status": {status.name: int(status) for status in Status}})


def _points(recording):
    """The one trajectory of a `(frames, signals, dims)` recording: the average of the markers, frame by frame (in
    signal order), as the feature averaged them itself before the one-point-per-frame decision of 2026-10-14."""
    with np.errstate(invalid="ignore", over="ignore"):  # an infinite marker is data
        return np.stack([np.ascontiguousarray(frame).mean(axis=0) for frame in recording])


def test_one_point_per_frame_reproduces_the_frozen_outputs_of_the_signals_form():
    """The outputs the feature gave before 2026-10-14, when it took `(signals, dims)` frames and averaged them itself
    (frozen, `dims` given), bit for bit with NaN equal: the averaged trajectory goes through `run` and `process` and
    the numbers are the same. The file was not regenerated; the recordings with a non-finite point are not compared
    (the old feature kept a NaN in its window, the new one rejects the point and does not buffer it; see
    `test_a_non_finite_point_is_rejected_and_not_buffered`)."""
    reference = np.load(REFERENCE)
    for name, recording in _recordings().items():
        points = _points(recording)
        if not np.isfinite(points).all():
            continue
        for index, params in enumerate(PARAMETER_SETS):
            if params["window"] > len(recording):
                continue
            key = f"{name}|{index}"
            columns = _frame(DirectionChange(**params).run(points))
            assert [c for c in columns.columns] == [c.split("|")[-1] for c in reference.files if c.startswith(key + "|") and not c.endswith("|stat")]
            for column in columns.columns:
                assert_same_floats(columns[column].to_numpy(), reference[f"{key}|{column}"], err_msg=f"{key} {column}")
            feature = DirectionChange(**params)
            assert [feature.process(point).status.name for point in points] == list(reference[f"{key}|stat"])
            if recording.shape[1] == 1:  # a single signal is its own trajectory
                np.testing.assert_array_equal(_bits(_frame(DirectionChange(**params).run(recording[:, 0, :])).to_numpy()), _bits(columns.to_numpy()))


def test_a_non_finite_point_is_rejected_and_not_buffered():
    points = _points(_recordings()["nan"])
    rejected = ~np.isfinite(points).all(axis=1)
    assert rejected.any()
    for params in PARAMETER_SETS[:2]:
        feature, never_saw_it = DirectionChange(**params), DirectionChange(**params)
        for point, bad in zip(points, rejected):
            result = feature.process(point)
            if bad:
                assert result.status is Status.INVALID_INPUT and not any(result.valid.values())
            else:
                expected = never_saw_it.process(point)
                assert result.status == expected.status
                assert np.array_equal(result.to_array(), expected.to_array(), equal_nan=True)  # two runs of this build: exact


def test_a_frame_is_one_point():
    """A `(signals, D)` frame is rejected by the shape check (the averaging of markers is the user's), and so is any
    number of coordinates but 2 or 3."""
    for bad in (np.zeros(4), np.zeros(1), np.zeros((2, 4)), np.zeros((2, 3)), np.zeros((2, 2, 3)), 5.0):
        with pytest.raises(ValueError):
            DirectionChange(window=3).process(bad)
    with pytest.raises(ValueError, match="2 or 3 coordinates"):
        DirectionChange(window=3).run(np.zeros((5, 4)))
    with pytest.raises(ValueError, match="DirectionChange"):
        DirectionChange(window=3).run(np.zeros((5, 2, 3)))
    with pytest.raises(TypeError):
        DirectionChange(window=3, dims=3)
