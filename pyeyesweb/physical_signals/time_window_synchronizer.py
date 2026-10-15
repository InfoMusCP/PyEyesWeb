"""Cut asynchronous streams into windows of the same duration (EyesWeb Synchronizer).

This is stream plumbing, not a feature: it has no :class:`~pyeyesweb.data_models.Result` and is not in
:func:`pyeyesweb.catalog`. Use it to feed several features with data that arrives in chunks of different sizes and
rates (audio, motion capture, video frames).
"""

import dataclasses
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

from pyeyesweb._core import core

_Synchronizer = core.base.TimeWindowSynchronizer


@dataclasses.dataclass(frozen=True)
class SynchronizedWindow:
    """One window of every stream, as returned by :meth:`TimeWindowSynchronizer.pop`.

    Attributes
    ----------
    start_time : float
        Presentation time of the start of the window, in seconds.
    duration : float
        Duration of the window, in seconds (the ``window`` of the synchronizer).
    samples : tuple of (ndarray or None)
        One entry per stream, in the order of the ``inputs`` of the synchronizer: a ``(samples, channels)`` array for a
        sampled stream, ``None`` for a frame stream.
    frames : tuple
        One entry per stream: the latest frame that starts before the end of the window for a frame stream (``None``
        before any frame arrived), ``None`` for a sampled stream.
    """

    start_time: float
    duration: float
    samples: Tuple[Optional[np.ndarray], ...]
    frames: Tuple[Any, ...]


class TimeWindowSynchronizer:
    r"""Re-chunk streams into windows that cover the same interval :math:`[t, t + \mathrm{window})`.

    Sensors and media rarely deliver data in blocks of the same size or at the same rate: audio comes in thousands of
    samples, motion capture in a few, video in single frames. The synchronizer buffers every stream and releases, one window
    at a time, the data of the same stretch of time, ready to be given together to features that need aligned inputs;
    :math:`t` advances by one window at each ``pop()``. A sampled stream (audio, motion capture, any time series) gives
    ``int(sampling_rate * window)`` samples per window, cut from and concatenated over the chunks received: samples that do
    not fit stay for the next window. A frame stream (video) gives the latest frame that starts before the end of the
    window. The synchronizer is pull-based: ``push`` and ``push_frame`` add data, ``ready()`` says whether every stream
    holds enough for the next window and ``pop()`` returns it.

    Parameters
    ----------
    window : float
        Duration of every window in seconds, > 0; it must hold at least one sample of every sampled stream.
    inputs : sequence of (int, float) or None
        One entry per stream, in the order used by ``push``: ``(channels, sampling_rate)`` for a sampled stream (the rate
        in Hz), ``None`` for a frame stream.
    start_time : float, default 0.0
        Presentation time in seconds of the start of the first window.

    Notes
    -----
    ``push(stream, samples, timestamp=None)`` adds a ``(samples, channels)`` chunk to a sampled stream (a 1-D array is one
    channel); with ``timestamp`` (seconds, of the first sample) the samples older than the start of the next window are
    dropped. ``push_frame(stream, frame, timestamp)`` adds a frame (any object) with its presentation time in seconds.
    ``pop()`` returns a :class:`SynchronizedWindow` and raises ``RuntimeError`` when ``ready()`` is false;
    ``samples_per_window(stream)`` gives the samples of a window of a sampled stream (0 for a frame stream); ``reset()``
    drops everything buffered and restarts at ``start_time``.

    **Corrected in the core.** The part of a chunk that did not fit in a window is kept and opens the next window (the
    original dropped it as soon as a window was full). Unlike the EyesWeb block, which outputs once per activation and
    possibly an incomplete window, this one outputs only complete windows.

    Examples
    --------
    >>> import numpy as np
    >>> from pyeyesweb.physical_signals import TimeWindowSynchronizer
    >>> sync = TimeWindowSynchronizer(0.04, [(1, 100.0), None])      # a 100 Hz signal and a video, windows of 40 ms
    >>> sync.push(0, np.arange(3.0))                                 # 3 of the 4 samples of the first window
    >>> sync.push_frame(1, "frame", timestamp=0.01)
    >>> sync.ready()
    False
    >>> sync.push(0, np.arange(3.0, 6.0))                            # the extra 2 samples stay for the next window
    >>> window = sync.pop()
    >>> window.samples[0].ravel().tolist(), window.frames[1], window.start_time
    ([0.0, 1.0, 2.0, 3.0], 'frame', 0.0)
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
