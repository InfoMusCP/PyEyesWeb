"""The call contract shared by every feature: declared inputs and outputs, `process`, `run`, `reset`.

    feature.inputs                 what one call receives (before any data)
    feature.outputs                what it returns (before any data)
    feature.process(*sample, timestamp=None)     one frame or sample, streaming: returns a `Result`
    feature.run(*data, timestamps=None)         a whole recording, offline: returns a `Recorder`
    feature.reset()                forget the accumulated state

`process` keeps state between calls (previous frames, the window being filled). `run` starts from a fresh state
by default (`reset=True`), so `run(recording)` is a pure function of the recording: the same input gives the same
output however often it is called. Pass `reset=False` to continue from the previous call, e.g. to process a long
recording in chunks. Both give the same numbers; tests check it.

Time is optional and in seconds: `timestamp` is the timestamp of the sample, `timestamps` of `run` one per sample. Nothing is
stamped with the wall clock.

Features that work on a window of samples own their buffer (`WindowedFeature`): they are configured with `window`
and `hop` and receive samples.
"""

import functools
import inspect
import math
import types
from abc import ABC, abstractmethod
from typing import Any, Mapping, Optional

import numpy as np

from .base import OutputsMixin
from .inputs import Input, InputKind, Inputs
from .recorder import Recorder
from .results import Result, Status


_UNSET = object()


def _recording(series: Any, declared: Input) -> Any:
    """One input's recording, indexed by time: float64 for the numeric kinds, the frames as they are for images."""
    if declared.kind is InputKind.IMAGE:
        return series if isinstance(series, (np.ndarray, list, tuple)) else list(series)
    return np.asarray(series, dtype=float)


def _checked(method, window: bool):
    """`process` / `_process_window` of a feature, preceded by the check of the call against the declared inputs: a
    wrong shape raises, a value that is not data (NaN, infinity, a missing joint, a time that goes back) returns
    `INVALID_INPUT` before the feature sees the sample."""

    @functools.wraps(method)
    def wrapper(self, *sample, **kwargs):
        try:
            inputs = self.inputs
        except NotImplementedError:
            return method(self, *sample, **kwargs)
        if window:
            inputs.check_windows(sample, type(self).__name__)  # the samples of a window were accepted by `process`
        else:
            inputs.check(sample, type(self).__name__)
            if reason := self._input_problem(sample, kwargs.get("timestamp")):
                return self._no_output(Status.INVALID_INPUT, reason, kwargs.get("timestamp"))
        return method(self, *sample, **kwargs)

    wrapper._input_checked = True
    return wrapper


def _remembering(method):
    """`process` of a feature, followed by the memory of its last result with status `OK` (`Feature.latest`)."""

    @functools.wraps(method)
    def wrapper(self, *sample, **kwargs):
        result = method(self, *sample, **kwargs)
        if isinstance(result, Result) and result.ok:
            self.__dict__["_latest"] = result
        return result

    wrapper._remembers = True
    return wrapper


def _forgetting(method):
    """`reset` of a feature, followed by the loss of the remembered result."""

    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        outcome = method(self, *args, **kwargs)
        self.__dict__.pop("_latest", None)
        return outcome

    wrapper._forgets = True
    return wrapper


class Feature(OutputsMixin, ABC):
    """Base of every feature. Subclasses declare `_INPUTS` / `_inputs()` and `_OUTPUTS` / `_schema()` and implement
    `process`; `run` is derived from it (a feature with a batch fast path overrides `run`).

    A feature with several inputs (a pair of signals) takes them as positional arguments in the order of `inputs`:
    `process(first, second, timestamp=None)` and `run(first, second, timestamps=None)`. `timestamp` and `timestamps` are keyword-only.
    """

    _INPUTS: Optional[Inputs] = None

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Every `process` (and `_process_window`) a subclass defines checks its arguments against `inputs` first.

        A wrong shape raises `ValueError` naming the feature and the input; an empty frame is not a shape error and
        goes through; NaN or infinity returns `INVALID_INPUT` (`Input.problem`).
        """
        super().__init_subclass__(**kwargs)
        for name, window in (("process", False), ("_process_window", True)):
            method = cls.__dict__.get(name)
            if callable(method) and not getattr(method, "__isabstractmethod__", False) \
                    and not getattr(method, "_input_checked", False):
                setattr(cls, name, _checked(method, window))
        process, reset = cls.__dict__.get("process"), cls.__dict__.get("reset")
        if callable(process) and not getattr(process, "__isabstractmethod__", False) and not getattr(process, "_remembers", False):
            cls.process = _remembering(cls.__dict__["process"])
        if callable(reset) and not getattr(reset, "_forgets", False):
            cls.reset = _forgetting(reset)

    @property
    def latest(self) -> Optional[Result]:
        """The last result with status `OK`, or `None` before the first one (and after `reset()`).

        Between two windows (`NO_OUTPUT`), during warm-up and on invalid input a call returns no new measurement; a
        caller that needs a continuous signal holds this value: `result if result.ok else feature.latest`.
        """
        return self.__dict__.get("_latest")

    @property
    def parameters(self) -> Mapping[str, Any]:
        """The parameters of the constructor with their current values, read-only (as scikit-learn's `get_params`).
        Change one by assigning it: `feature.window = 50`. A parameter the feature resolves at construction and does not keep
        (`skeleton`, which becomes `labels`, `weights` and `pairs`) is not listed."""
        names = (name for name, parameter in inspect.signature(type(self)).parameters.items()
                 if parameter.kind not in (parameter.VAR_POSITIONAL, parameter.VAR_KEYWORD))
        values = {name: getattr(self, name, _UNSET) for name in names}
        return types.MappingProxyType({name: value for name, value in values.items() if value is not _UNSET})

    def _inputs(self) -> Inputs:
        if self._INPUTS is None:
            raise NotImplementedError(f"{type(self).__name__} must define _INPUTS or override _inputs()")
        return self._INPUTS

    @property
    def inputs(self) -> Inputs:
        """What one call receives: kind, shape, labels. Known from the constructor parameters alone."""
        inputs = self.__dict__.get("_inputs_cache")
        if inputs is None:
            inputs = self.__dict__["_inputs_cache"] = self._inputs()
        return inputs

    def _input_problem(self, sample: Any, timestamp: Optional[float]) -> str:
        """Why this call is not data, or `""`: the central rules of the call contract (a subclass adds its own and
        calls `super()`). Raises `ValueError` for a call that cannot be meant (a wrong shape, an unknown joint name)."""
        if timestamp is not None and not math.isfinite(timestamp):
            return "non-finite timestamp"
        return self.inputs.problem(sample)

    @abstractmethod
    def process(self, *sample: Any, timestamp: Optional[float] = None) -> Result:
        """Process one sample or frame per input (see `inputs`) and return the result. `timestamp`: timestamp in seconds."""

    def run(self, *data: Any, timestamps: Optional[Any] = None, reset: bool = True) -> Recorder:
        """Process a whole recording and return a `Recorder` with one row per sample (frame).

        Parameters
        ----------
        *data : array-like
            One array per input, first axis = time (see `inputs` for the shape of one sample).
        timestamps : array-like, optional
            Timestamps in seconds, one per sample.
        reset : bool, optional
            Start from a fresh state (default), or continue from the previous call.
        """
        self.inputs._check_count(data, type(self).__name__)  # the optional last inputs may be left out
        if reset:
            self.reset()
        arrays = [_recording(series, declared) for series, declared in zip(data, self.inputs)]
        row_count = len(arrays[0])
        if any(len(array) != row_count for array in arrays):
            raise ValueError("every input must have the same number of samples")
        self._check_recording(arrays)
        if timestamps is not None:
            timestamps = np.asarray(timestamps, dtype=float)
            if timestamps.shape != (row_count,):
                raise ValueError("timestamps must hold one timestamp per sample")
        results = (self.process(*(array[index] for array in arrays), timestamp=None if timestamps is None else float(timestamps[index])) for index in range(row_count))
        first = next(results, None)  # the first sample may fix the outputs (a dimension taken from the data)
        recorder = Recorder(self, capacity=max(row_count, 1))
        if first is not None:
            recorder.append(first)
            recorder.extend(results)
        return recorder

    def _check_recording(self, arrays: Any) -> None:
        """Check the first sample of each recording against `inputs`, so `run` fails before it starts."""
        if all(len(array) for array in arrays):
            self.inputs.check([array[0] for array in arrays], type(self).__name__)

    def reset(self) -> None:
        """Forget the state accumulated by `process` (no-op for stateless features)."""


class WindowedFeature(Feature):
    """A feature computed on a window of samples that it buffers itself.

    Parameters
    ----------
    window : int
        Samples per window.
    hop : int, optional
        New samples between two windows (default 1: a result for every sample once the window is full).

    `process(sample)` returns `WARMING_UP` until the first window is full and `NO_OUTPUT` between hops; when a window
    is ready it calls `_process_window(series)`, where `series` is `(channels, window)` with the oldest sample first
    (one such array per input for a feature with several inputs). `_process_window` is the private hook a subclass implements.
    The first frame after `reset()` fixes the number of values of a frame; a frame of another size raises `ValueError`.
    """

    def __init__(self, window: int, hop: int = 1, **params: Any):
        self._window, self._hop = self._validated(window, hop)
        self._buffer = None
        self._pushed = 0
        super().__init__(**params)

    @classmethod
    def _validated(cls, window: int, hop: int) -> tuple:
        window, hop = int(window), int(hop)
        if window < 1 or not 1 <= hop <= window:
            raise ValueError(f"{cls.__name__}: window must be >= 1 and 1 <= hop <= window (got window={window}, hop={hop})")
        return window, hop

    @property
    def window(self) -> int:
        """Samples per window; setting it keeps the newest samples (see `configure`)."""
        return self._window

    @window.setter
    def window(self, value: int) -> None:
        self.configure(window=value)

    @property
    def hop(self) -> int:
        """New samples between two windows; setting it keeps the newest samples (see `configure`)."""
        return self._hop

    @hop.setter
    def hop(self, value: int) -> None:
        self.configure(hop=value)

    def configure(self, window: Optional[int] = None, hop: Optional[int] = None) -> None:
        """Change `window` and / or `hop` together (validated as in the constructor), keeping the newest samples."""
        old_window = self._window
        window, hop = self._validated(self._window if window is None else window, self._hop if hop is None else hop)
        if self._buffer is not None:
            self._buffer.reconfigure(window, window - hop)
            self._pushed = min(self._pushed, old_window, window)  # the samples the buffer holds
        self._window, self._hop = window, hop
        self._window_changed()

    def _window_changed(self) -> None:
        """Called after `window` or `hop` changed: a feature whose block depends on them updates it here."""

    @abstractmethod
    def _process_window(self, *series: Any, timestamp: Optional[float] = None) -> Result:
        """The hook subclasses implement: the feature of one complete window `(channels, window)` per input.

        Private: `process` calls it once the buffer holds a full window.
        """

    def process(self, *sample: Any, timestamp: Optional[float] = None) -> Result:
        samples = [np.asarray(part, dtype=float).ravel() for part in sample]
        if not samples or any(array_of_input.size == 0 for array_of_input in samples):
            return self._no_output(Status.INVALID_INPUT, "empty sample", timestamp)
        sizes = tuple(array_of_input.size for array_of_input in samples)
        if self._buffer is None:
            self._open_buffer(sizes)
        elif self._sizes != sizes:
            raise ValueError(f"{type(self).__name__}: expected {sum(self._sizes)} values per frame, got {sum(sizes)}: "
                             "the size of the frame must not change between calls; call reset() to start a new recording")
        self._pushed += 1
        if not self._buffer.push(np.concatenate(samples)):
            if self._pushed < self.window:
                return self._no_output(Status.WARMING_UP, f"{self._pushed} of {self.window} samples", timestamp)
            return self._no_output(Status.NO_OUTPUT, "between windows", timestamp)
        window = self._buffer.window()
        return self._process_window(*np.split(window, np.cumsum(self._sizes)[:-1], axis=0), timestamp=timestamp)

    def reset(self) -> None:
        self._buffer = None
        self._pushed = 0
        super().reset()

    def _open_buffer(self, sizes: tuple) -> None:
        from pyeyesweb._core import core
        self._buffer = core.SeriesBuffer(sum(sizes), self.window, self.window - self.hop)
        self._sizes = sizes
        self._pushed = 0


