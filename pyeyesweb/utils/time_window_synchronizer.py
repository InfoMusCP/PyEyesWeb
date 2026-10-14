"""Cut asynchronous streams into windows of the same duration (EyesWeb Synchronizer).

This is stream plumbing, not a feature: it has no `Result` and is not in `pyeyesweb.catalog()`. Use it to feed several
features with data that arrives in chunks of different sizes and rates (audio, motion capture, video frames).
"""

import dataclasses
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

from pyeyesweb._core import core

_Synchronizer = core.base.TimeWindowSynchronizer


@dataclasses.dataclass(frozen=True)
class SynchronizedWindow:
    """One window of every stream: `samples[i]` is a `(samples, channels)` array for a sampled stream and `None` for a
    frame stream, whose latest frame is `frames[i]` (`None` for a sampled stream or before any frame arrived)."""

    start_time: float
    duration: float
    samples: Tuple[Optional[np.ndarray], ...]
    frames: Tuple[Any, ...]


class TimeWindowSynchronizer:
    """Re-chunk streams into windows that cover the same interval `[t, t + window)`, `t` advancing by one window.

    A sampled stream (audio, motion capture, any time series) gives `int(sampling_rate * window)` samples per window,
    cut from and concatenated over the chunks received: samples that do not fit stay for the next window. A frame stream
    (video) gives the latest frame that starts before the end of the window.

    Parameters
    ----------
    window : float
        Duration of every window in seconds, > 0; it must hold at least one sample of every sampled stream.
    inputs : sequence of (int, float) or None
        One entry per stream, in the order used by `push`: `(channels, sampling_rate)` for a sampled stream (the rate
        in Hz), `None` for a frame stream.
    start_time : float, optional
        Presentation time in seconds of the start of the first window (default 0).

    Examples
    --------
    >>> sync = TimeWindowSynchronizer(0.04, [(2, 48000.0), (51, 100.0), None])   # audio, mocap, video
    >>> sync.push(0, audio_chunk)                    # (samples, 2)
    >>> sync.push(1, mocap_chunk)                    # (samples, 51)
    >>> sync.push_frame(2, frame, timestamp=0.01)
    >>> while sync.ready():
    ...     window = sync.pop()                      # window.samples[0] is (1920, 2)
    """

    def __init__(self, window: float, inputs: Sequence[Optional[Tuple[int, float]]], start_time: float = 0.0):
        self._window = float(window)
        self._start_time = float(start_time)
        self._core = _Synchronizer(self._window, [_Synchronizer.Input.frames() if stream is None else _Synchronizer.Input(*stream)
                                                  for stream in inputs], self._start_time)
        self._sampled = tuple(stream is not None for stream in inputs)
        self._frames: List[Dict[int, Any]] = [{} for _ in inputs]
        self._counter = 0

    @property
    def window(self) -> float:
        """Duration of a window in seconds."""
        return self._window

    @property
    def start_time(self) -> float:
        """Presentation time in seconds of the start of the first window."""
        return self._start_time

    def samples_per_window(self, stream: int) -> int:
        """Samples of one window of a sampled stream (0 for a frame stream)."""
        return self._core.samples_per_window(stream)

    def push(self, stream: int, samples: Any, timestamp: Optional[float] = None) -> None:
        """Add a chunk `(samples, channels)` to a sampled stream (a 1-D array is one channel).

        With `timestamp` (seconds, of the first sample) the samples older than the start of the next window are dropped.
        """
        chunk = np.asarray(samples, dtype=float)
        if chunk.ndim == 1:
            chunk = chunk[:, None]
        if chunk.ndim != 2:
            raise ValueError(f"samples must be (samples, channels), got shape {chunk.shape}")
        self._core.push_samples(stream, np.ascontiguousarray(chunk.T), timestamp)

    def push_frame(self, stream: int, frame: Any, timestamp: float) -> None:
        """Add a frame (any object) with its presentation time in seconds to a frame stream."""
        token = self._counter + 1
        self._core.push_frame(stream, token, timestamp)  # raises for an unknown stream or a sampled one
        self._counter = token
        self._frames[stream][token] = frame

    def ready(self) -> bool:
        """Whether every stream holds enough for the next window."""
        return self._core.ready()

    def pop(self) -> SynchronizedWindow:
        """The next window; call only when `ready()` (otherwise a `RuntimeError`)."""
        start_time, duration, samples, tokens = self._core.pop()
        frames = []
        for stream, token in enumerate(tokens):
            if self._sampled[stream]:
                frames.append(None)
                continue
            frames.append(self._frames[stream].get(token))
            self._frames[stream] = {key: frame for key, frame in self._frames[stream].items() if key >= token}  # older ones are gone
        return SynchronizedWindow(start_time, duration, tuple(None if block is None else np.ascontiguousarray(block.T)
                                                               for block in samples), tuple(frames))

    def reset(self) -> None:
        """Drop everything buffered and restart at the start time."""
        self._core.reset()
        self._frames = [{} for _ in self._frames]
