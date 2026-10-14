"""The time rule (`DEVELOPMENT_SPEC.md` section 3) on every `_timed` feature of `catalog()`, driven by the recordings of
`test_contract_all_features`:

* after the first timed call a timestamp that is not larger than the previous one is `INVALID_INPUT` ("non-increasing
  timestamp"), with empty outputs, and changes nothing: the call after it behaves as if it had not happened;
* the first timed call has no previous timestamp: its step is `1 / sampling_rate`, else 1 s per sample (with the note in
  `reason`), whatever its absolute value (epoch seconds, 1e9);
* a call without timestamp takes the same fallback step and makes the previous timestamp unknown, so the next timed call
  is a first one again.
"""

import numpy as np
import pytest

pytest.importorskip("pyeyesweb._core", exc_type=ImportError)

from test_contract_all_features import factory_and_recordings  # noqa: E402

from pyeyesweb import catalog  # noqa: E402
from pyeyesweb.data_models import Status  # noqa: E402

TIMED = [info.name for info in catalog() if getattr(info.cls, "_timed", False)]
STEP = 2 ** -6  # exactly representable next to 1e9: the epoch case differs from the small one only by the rule


def _feature_and_frames(name):
    factory, recordings = factory_and_recordings(name)
    return factory, lambda index: tuple(recording[index] for recording in recordings)


def _same(first, second):
    return first.status == second.status and first.reason == second.reason and first == second


def test_there_are_timed_features():
    assert len(TIMED) >= 8


@pytest.mark.parametrize("name", TIMED)
@pytest.mark.parametrize("bad", [1.0 + STEP, 0.5], ids=["repeated", "decreasing"])
def test_a_timestamp_that_does_not_increase_is_rejected_and_changes_nothing(name, bad):
    factory, frame = _feature_and_frames(name)
    feature, baseline = factory(), factory()
    for index, stamp in enumerate((1.0, 1.0 + STEP)):
        feature.process(*frame(index), timestamp=stamp)
        baseline.process(*frame(index), timestamp=stamp)
    rejected = feature.process(*frame(2), timestamp=bad)
    assert rejected.status is Status.INVALID_INPUT and rejected.reason.startswith("non-increasing timestamp")
    assert not any(rejected.valid.values())
    after, expected = feature.process(*frame(2), timestamp=1.0 + 2 * STEP), baseline.process(*frame(2), timestamp=1.0 + 2 * STEP)
    assert after.status is expected.status and _same(after, expected)


@pytest.mark.parametrize("name", TIMED)
def test_the_first_timed_call_is_a_first_call_whatever_its_time(name):
    factory, frame = _feature_and_frames(name)
    epoch, small = factory(), factory()
    for index in range(4):
        got = epoch.process(*frame(index), timestamp=1e9 + index * STEP)
        expected = small.process(*frame(index), timestamp=0.5 + index * STEP)
        assert _same(got, expected), (index, got, expected)


@pytest.mark.parametrize("name", TIMED)
def test_a_call_without_timestamp_makes_the_next_timed_call_a_first_one(name):
    factory, frame = _feature_and_frames(name)
    mixed, untimed = factory(), factory()
    for index, stamp in enumerate((100.0, 100.0 + STEP)):
        mixed.process(*frame(index), timestamp=stamp)
        untimed.process(*frame(index), timestamp=stamp)
    assert _same(mixed.process(*frame(2)), untimed.process(*frame(2)))
    got, expected = mixed.process(*frame(3), timestamp=1e9), untimed.process(*frame(3))  # not a step of 1e9 s
    assert _same(got, expected), (got, expected)
    assert mixed.process(*frame(4), timestamp=1e9 + STEP).status is not Status.INVALID_INPUT


@pytest.mark.parametrize("name", TIMED)
def test_run_agrees_with_process_on_a_repeated_timestamp(name):
    factory, recordings = factory_and_recordings(name)
    count = len(recordings[0])
    stamps = 1.0 + STEP * np.arange(count)
    stamps[5] = stamps[4]
    recorded = factory().run(*recordings, timestamps=stamps)
    loop = factory()
    rows = [loop.process(*(recording[index] for recording in recordings), timestamp=stamps[index]) for index in range(count)]
    assert [int(status) for status in recorded.status] == [int(row.status) for row in rows]
    assert recorded.status[5] == Status.INVALID_INPUT
