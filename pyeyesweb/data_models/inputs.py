"""Declared inputs of a feature, the counterpart of the declared outputs (`Schema`).

A feature states once what one call to `process` receives: `feature.inputs`. It is available before any data
arrives, so channels, joint lists and recordings can be validated and shaped without trial and error.

| Kind | One call receives | `run` receives |
|---|---|---|
| `SAMPLE` | a vector of `C` channel values (a scalar signal has `C = 1`); an event train is a sample stream in which a non-zero value is an event | `(T, C)` or `(T,)` |
| `POINTS` | one frame of `N` labelled points of dimension `D`: an `(N, D)` array | `(T, N, D)` |
| `MATRIX` | one `(R, C)` matrix, e.g. the output of another feature | `(T, R, C)` |
| `IMAGE` | one 8-bit image: `(H, W)`, or `(H, W, C)`; a `bool` array is a 0 / 1 mask | `(T, H, W)` or `(T, H, W, C)`, or a list of images |

A feature with several inputs lists them in call order.

Every call is checked against these declarations before the feature sees it (`Input.check`, applied by `Feature`): a
sample of the wrong size, a frame of the wrong rank, dimension or number of points raises `ValueError`. An empty
sample or frame is not a shape error and reaches the feature, which reports `INVALID_INPUT`. An input that also takes
another object (a dict of labelled points) lists its type in `accepts`; such a value is not shape-checked.

A numeric input holding NaN or infinity is not data: the call gives `INVALID_INPUT` ("NaN or infinite values") and the
sample goes nowhere (`Input.problem`, applied by `Feature`). An input for which NaN is meaningful (a dropout) says
`allow_non_finite=True` and checks the values itself.
"""

import enum
from dataclasses import dataclass
from typing import Any, Iterator, Optional, Tuple

import numpy as np

NON_FINITE = "NaN or infinite values"
_INTEGER_LIMIT = 2 ** 31 - 1  # the largest value a block that takes an `int` accepts


class InputKind(enum.Enum):
    SAMPLE = "sample"
    POINTS = "points"
    MATRIX = "matrix"
    IMAGE = "image"


@dataclass(frozen=True)
class Input:
    """One input of a feature.

    Parameters
    ----------
    name : str
        What the input is (`"speed"`, `"skeleton"`).
    kind : InputKind
        What one call receives.
    shape : tuple of int or None
        Shape of one call's data; `None` for an entry means "set by the constructor parameters or the data".
    labels : sequence of str, optional
        Names of the joints / channels, in the order of the arrays, when the feature was given them.
    unit, doc : str, optional
        Unit and description.
    accepts : tuple of type, optional
        Extra types the feature takes as they are (e.g. `dict` for a labelled set of points); they are
        not shape-checked.
    optional : bool, optional
        The call may leave this input out (only the last inputs can be optional).
    allow_non_finite : bool, optional
        NaN and infinity are meaningful values of this input (dropouts): they are not rejected centrally.
    integer : bool, optional
        The feature turns the values into integers: values beyond the integer range are rejected too.
    """

    name: str
    kind: InputKind
    shape: Tuple[Optional[int], ...] = ()
    labels: Optional[Tuple[str, ...]] = None
    unit: str = ""
    doc: str = ""
    accepts: Tuple[type, ...] = ()
    optional: bool = False
    allow_non_finite: bool = False
    integer: bool = False

    def check(self, value: Any, owner: str = "feature") -> None:
        """Raise `ValueError` when `value` does not fit this input; `owner` names the feature in the message.

        `SAMPLE`: a scalar or a 1-D vector of `shape[0]` values. `POINTS` and `MATRIX`: a 2-D array whose axes match
        the declared ints (and `len(labels)` rows when labelled). `IMAGE`: a 2-D `(H, W)` or 3-D `(H, W, C)` array of
        pixel values 0-255 (any numeric dtype holding whole numbers in that range, or `bool`); `shape` is the declared
        `(H, W)` or `(H, W, C)`, where a 2-D declaration means one channel and a 2-D array counts as one channel.
        `None` in `shape` is free. Anything with no element is let through: an empty frame is a data problem, reported
        by the feature as `INVALID_INPUT`.
        """
        if self.accepts and isinstance(value, self.accepts):
            return
        if self.kind is InputKind.IMAGE:
            self._check_image(value, owner)
            return
        try:
            array = np.asarray(value, dtype=float)
        except (TypeError, ValueError):
            raise ValueError(f"{owner}: input '{self.name}' expects {self._expected()}, "
                             f"got {type(value).__name__} that is not a numeric array") from None
        if array.size == 0:
            return
        got = array.shape
        want = self._wanted()
        if self.kind is InputKind.SAMPLE:
            if array.ndim > 1 or (want and want[0] is not None and array.size != want[0]):
                self._fail(owner, got)
            return
        if array.ndim != 2 or any(expected is not None and expected != actual for expected, actual in zip(want, got)):
            self._fail(owner, got)

    def problem(self, value: Any) -> str:
        """The reason the numbers of `value` cannot be processed, or `""`: NaN or infinity (unless `allow_non_finite`),
        or beyond the integer range for an `integer` input. Images are not checked."""
        if self.kind is InputKind.IMAGE or self.allow_non_finite:
            return ""
        try:
            array = np.asarray(list(value.values()) if isinstance(value, dict) else value, dtype=float)
        except (TypeError, ValueError):
            return ""
        if not np.isfinite(array).all():
            return NON_FINITE
        return "value outside the integer range" if self.integer and np.abs(array).max(initial=0.0) > _INTEGER_LIMIT else ""

    def _check_image(self, value: Any, owner: str) -> None:
        try:
            array = np.asarray(value)
        except (TypeError, ValueError):
            array = None
        if array is None or array.dtype.kind not in "biuf":
            raise ValueError(f"{owner}: input '{self.name}' expects {self._expected()}, "
                             f"got {type(value).__name__} that is not a numeric array")
        if array.size == 0:
            return
        channels = array.shape[2] if array.ndim == 3 else 1
        wanted_channels = self.shape[2] if len(self.shape) > 2 else 1  # a 2-D declaration is one channel
        sizes_differ = any(expected is not None and expected != actual for expected, actual in zip(self.shape[:2], array.shape[:2]))
        if array.ndim not in (2, 3) or sizes_differ or (wanted_channels is not None and channels != wanted_channels):
            self._fail(owner, array.shape)
        if array.dtype != np.uint8 and array.dtype.kind != "b" and not (
                np.isfinite(array).all() and (array == np.floor(array)).all() and array.min() >= 0 and array.max() <= 255):
            raise ValueError(f"{owner}: input '{self.name}' expects whole-number pixel values in 0-255, "
                             f"got {array.dtype} values from {array.min()} to {array.max()}")

    def check_window(self, series: Any, owner: str = "feature") -> None:
        """Raise `ValueError` when a complete window `(channels, window)` cannot hold this input.

        `SAMPLE`: `shape[0]` channels. `POINTS` / `MATRIX`: frames are flattened row-major, so the channels are
        `rows * shape[1]` (a multiple of `shape[1]` when the number of rows is free).
        """
        array = np.asarray(series, dtype=float)
        want = self._wanted()
        if array.size == 0 or not want:
            return
        channels = array.shape[0] if array.ndim == 2 else 1  # a 1-D window is one channel
        if self.kind is InputKind.SAMPLE:
            ok = array.ndim <= 2 and (want[0] is None or channels == want[0])
            expected = f"{want[0] if want[0] is not None else 'any number of'} channels"
        else:
            dimension = want[1] if len(want) > 1 else None
            rows = want[0]
            ok = array.ndim <= 2 and (dimension is None or (channels % dimension == 0 and (rows is None or channels == rows * dimension)))
            expected = (f"frames of shape ({'any' if rows is None else rows}, {'any' if dimension is None else dimension}) "
                        "flattened to channels")
        if not ok:
            raise ValueError(f"{owner}: input '{self.name}' expects a window (channels, window) with {expected}, "
                             f"got shape {array.shape}")

    def _wanted(self) -> Tuple[Optional[int], ...]:
        want = list(self.shape)
        if self.labels is not None and want and want[0] is None:
            want[0] = len(self.labels)
        return tuple(want)

    def _expected(self) -> str:
        dims = [("any" if size is None else str(size)) for size in self._wanted()]
        shape = "(" + ", ".join(dims) + ("," if len(dims) == 1 else "") + ")"
        labelled = f", one row per label ({len(self.labels)} labels)" if self.labels is not None else ""
        return f"{self.kind.value} of shape {shape}{labelled}"

    def _fail(self, owner: str, got: tuple) -> None:
        raise ValueError(f"{owner}: input '{self.name}' expects {self._expected()}, got shape {got}")

    def describe(self) -> str:
        shape = "(" + ", ".join("?" if size is None else str(size) for size in self.shape) + ")"
        unit = f" [{self.unit}]" if self.unit else ""
        return f"{self.name}: {self.kind.value} {shape}{unit}" + (f" - {self.doc}" if self.doc else "")


class Inputs:
    """The inputs of a feature, in call order. Iterable, indexable by position or name."""

    def __init__(self, *inputs: Input):
        self._inputs = tuple(inputs)

    def __iter__(self) -> Iterator[Input]:
        return iter(self._inputs)

    def __len__(self) -> int:
        return len(self._inputs)

    def __getitem__(self, key):
        if isinstance(key, str):
            for item in self._inputs:
                if item.name == key:
                    return item
            raise KeyError(key)
        return self._inputs[key]

    @property
    def names(self) -> Tuple[str, ...]:
        return tuple(spec.name for spec in self._inputs)

    def _check_count(self, values: Any, owner: str) -> None:
        required = sum(not declared.optional for declared in self._inputs)
        if not required <= len(values) <= len(self._inputs):
            raise ValueError(f"{owner}: takes {required if required == len(self._inputs) else f'{required} to {len(self._inputs)}'} "
                             f"input(s) ({', '.join(self.names)}), got {len(values)}")

    def check(self, values: Any, owner: str = "feature") -> None:
        """Check one value per input (`values` in call order)."""
        self._check_count(values, owner)
        for declared, value in zip(self._inputs, values):
            declared.check(value, owner)

    def problem(self, values: Any) -> str:
        """The first `Input.problem` of one value per input (`values` in call order), or `""`."""
        return next((reason for declared, value in zip(self._inputs, values) if (reason := declared.problem(value))), "")

    def check_windows(self, windows: Any, owner: str = "feature") -> None:
        """`Input.check_window` for one window per input."""
        self._check_count(windows, owner)
        for declared, window in zip(self._inputs, windows):
            declared.check_window(window, owner)

    def describe(self) -> str:
        return "\n".join(spec.describe() for spec in self._inputs)

    def __repr__(self) -> str:
        return "Inputs(" + ", ".join(spec.describe() for spec in self._inputs) + ")"
