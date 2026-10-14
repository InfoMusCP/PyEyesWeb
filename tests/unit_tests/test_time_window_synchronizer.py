"""TimeWindowSynchronizer (EyesWeb Synchronizer), the stream utility of `pyeyesweb.utils`. Needs the compiled core
(EYESWEB_CORE_PATH), else skipped."""
import os
import sys

import numpy as np
import pytest

if os.environ.get("EYESWEB_CORE_PATH"):
    sys.path.insert(0, os.environ["EYESWEB_CORE_PATH"])

pytest.importorskip("pyeyesweb._core", exc_type=ImportError)

from pyeyesweb import catalog  # noqa: E402
from pyeyesweb.utils.time_window_synchronizer import SynchronizedWindow, TimeWindowSynchronizer  # noqa: E402


def test_a_stream_is_cut_into_windows():
    sync = TimeWindowSynchronizer(0.1, [(2, 100.0)])
    assert sync.window == 0.1 and sync.start_time == 0.0 and sync.samples_per_window(0) == 10
    sync.push(0, np.arange(50.0).reshape(25, 2))
    assert sync.ready()
    window = sync.pop()
    assert isinstance(window, SynchronizedWindow) and window.start_time == 0.0 and window.duration == 0.1
    assert window.samples[0].shape == (10, 2) and window.samples[0][0].tolist() == [0.0, 1.0]
    assert window.frames == (None,)
    assert sync.pop().start_time == pytest.approx(0.1)
    assert not sync.ready()
    with pytest.raises(RuntimeError):
        sync.pop()


def test_what_a_chunk_leaves_over_opens_the_next_window():
    sync = TimeWindowSynchronizer(0.1, [(1, 100.0)])
    seen = []
    for chunk in range(6):  # chunks of 7 samples, windows of 10 (EyesWeb lost the rest of a chunk)
        sync.push(0, np.arange(chunk * 7.0, chunk * 7.0 + 7))
        while sync.ready():
            seen.extend(sync.pop().samples[0][:, 0])
    assert seen == list(range(40))


def test_streams_of_different_rates_and_frames_share_the_windows():
    sync = TimeWindowSynchronizer(0.04, [(2, 100.0), (1, 50.0), None])
    assert [sync.samples_per_window(index) for index in range(3)] == [4, 2, 0]
    sync.push(0, np.ones((4, 2)))
    assert not sync.ready()  # the second stream is missing
    sync.push(1, np.arange(2.0))
    sync.push_frame(2, "first", 0.0)
    sync.push_frame(2, "second", 0.03)
    sync.push_frame(2, "third", 0.05)
    window = sync.pop()
    assert window.samples[1].shape == (2, 1) and window.samples[2] is None and window.frames == (None, None, "second")
    sync.push(0, np.ones((4, 2)))
    sync.push(1, np.arange(2.0))
    assert sync.pop().frames[2] == "third"


def test_outdated_samples_are_dropped_with_a_timestamp():
    sync = TimeWindowSynchronizer(0.1, [(1, 100.0)], start_time=1.0)
    sync.push(0, np.arange(10.0))
    sync.pop()
    sync.push(0, np.arange(100.0, 115.0), timestamp=1.05)  # the first 5 samples are older than the window at 1.1
    assert sync.pop().samples[0][0, 0] == 105.0
    sync.reset()
    assert not sync.ready()
    sync.push(0, np.arange(10.0))
    assert sync.pop().start_time == 1.0


def test_wrong_use_raises():
    with pytest.raises(ValueError):
        TimeWindowSynchronizer(0.0, [(1, 100.0)])
    with pytest.raises(ValueError):
        TimeWindowSynchronizer(0.1, [])
    with pytest.raises(ValueError):
        TimeWindowSynchronizer(0.001, [(1, 100.0)])
    sync = TimeWindowSynchronizer(0.1, [(2, 100.0), None])
    with pytest.raises(ValueError):
        sync.push(0, np.ones((5, 3)))  # wrong channel count
    with pytest.raises(ValueError):
        sync.push(0, np.ones((5, 2, 2)))
    with pytest.raises(ValueError):
        sync.push(1, np.ones((5, 2)))  # not a sampled stream
    with pytest.raises(ValueError):
        sync.push_frame(0, "frame", 0.0)  # not a frame stream
    with pytest.raises(IndexError):
        sync.push_frame(7, "frame", 0.0)


def test_it_is_a_utility_not_a_feature():
    assert "TimeWindowSynchronizer" not in {info.name for info in catalog()}
