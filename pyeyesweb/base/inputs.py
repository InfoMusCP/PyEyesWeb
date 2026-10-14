"""Helpers shared by the features for declaring and reading their inputs."""

from typing import Any, Dict, Optional, Sequence, Tuple

import numpy as np

from pyeyesweb.data_models.inputs import Input, InputKind


def points_input(name: str, labels: Optional[Sequence[str]], doc: str, dims: int = 3, accepts: tuple = ()) -> Input:
    """The declared `POINTS` input of a feature that takes one `(N, dims)` frame, labelled when `labels` is given.

    `accepts`: extra types taken as they are (`dict` for a `label -> point` set).
    """
    return Input(name, InputKind.POINTS, (None if labels is None else len(labels), dims), labels, doc=doc,
                 accepts=accepts)


def image_input(name: str, doc: str, channels: Optional[int] = 1) -> Input:
    """The declared `IMAGE` input of a feature that takes one 8-bit image per call: `(H, W)` (also `(H, W, 1)`) for
    `channels=1`, `(H, W, C)` for `channels=C`, any number of channels for `channels=None`."""
    return Input(name, InputKind.IMAGE, (None, None) if channels == 1 else (None, None, channels), doc=doc)


def as_image(frame: Any) -> np.ndarray:
    """An image (already checked by its `Input`) as the C-contiguous `uint8` array the core takes; a `bool` mask is 0 / 1."""
    return np.ascontiguousarray(frame, dtype=np.uint8)


def labelled_set(frame: Any, labels: Optional[Sequence[str]], owner: str,
                 anonymous: bool = False, dims: int = 3) -> Dict[str, Tuple[float, ...]]:
    """A frame as the `label -> (x, y, z)` dict the core blocks take.

    `frame` is an `(N, dims)` array in the order of `labels`, or already such a dict (returned unchanged).
    With `anonymous=True` an array needs no labels (the points are named by their index); otherwise a missing
    `labels` raises `ValueError`, naming `owner` in the message.
    """
    if isinstance(frame, dict):
        return frame
    points = np.asarray(frame, dtype=float)
    if points.size == 0:  # an empty frame is data, not shape: the block reports it
        return {}
    if points.ndim != 2 or points.shape[1] != dims:
        raise ValueError(f"{owner}: expected an (N, {dims}) array of points, got shape {points.shape}")
    if labels is None:
        if not anonymous:
            raise ValueError(f"array input needs the joint names: construct with {owner}(labels=[...])")
        labels = [str(index) for index in range(len(points))]
    elif len(labels) != len(points):
        raise ValueError(f"{owner}: expected {len(labels)} points (one per label), got {len(points)}")
    return {label: tuple(point) for label, point in zip(labels, points.tolist())}


def scalar(value: Any) -> float:
    """One channel of a sample as a float: accepts a number or an array holding one value."""
    return np.asarray(value, dtype=float).item()


def train(value: Any) -> np.ndarray:
    """An event train (or one sample of it) as the 1-D float array the core takes."""
    return np.asarray(value, dtype=float).reshape(-1)


def non_finite(values: Any, allow_empty: bool = False) -> str:
    """The standard reason `values` cannot go to a block, or "" when it can: `"empty frame"` (unless `allow_empty`)
    or `"NaN or infinite values"`."""
    values = np.asarray(values, dtype=float)
    if values.size == 0:
        return "" if allow_empty else "empty frame"
    return "" if np.isfinite(values).all() else "NaN or infinite values"


def check_dims(dims: int) -> int:
    """Validate the number of dimensions of a movement vector."""
    if int(dims) < 1:
        raise ValueError("dims must be >= 1")
    return int(dims)


class InferredDims:
    """Mixin, placed before `WindowedFeature` or a frame feature, of a feature whose frames are `(dims,)` points with
    `dims` optional.

    `dims=None` is taken from the first frame given to `process`; `reset()` forgets it, and an explicit `dims` stays.
    The declared `inputs` follow (`(None,)` until the dimension is known).
    """

    _dims: Optional[int] = None
    _dims_inferred = False

    @property
    def dims(self) -> Optional[int]:
        return self._dims

    @dims.setter
    def dims(self, value: Optional[int]):
        self._set_dims(None if value is None else check_dims(value), inferred=False)

    def _set_dims(self, value: Optional[int], inferred: bool) -> None:
        self._dims, self._dims_inferred = value, inferred
        self._outputs_changed()  # the declared inputs depend on it

    def _frame_dims(self, frame: Any) -> Optional[int]:
        """The dimension a first frame shows, or `None` when it shows none: the length of a `(dims,)` point."""
        shape = np.shape(frame)
        return shape[0] if len(shape) == 1 and shape[0] >= 1 else None

    def _infer_dims(self, frame: Any) -> None:
        """Take `dims` from `frame` when it is not known yet."""
        if self._dims is None and (found := self._frame_dims(frame)):
            self._set_dims(found, inferred=True)

    def process(self, frame: Any, *, timestamp: Optional[float] = None):
        self._infer_dims(frame)
        return super().process(frame, timestamp=timestamp)

    def reset(self) -> None:
        if self._dims_inferred:
            self._set_dims(None, inferred=False)
        super().reset()

    def _window_trajectory(self, series: Any) -> np.ndarray:
        """A complete window `(dims, window)` as the `(window, dims)` trajectory the core works on.

        The dimension of the feature must be known; the central check has verified the channels against it.
        """
        if self._dims is None:
            raise ValueError(f"{type(self).__name__}: dims is unknown before the first frame; "
                             "construct with dims=... to analyse a window directly")
        return np.ascontiguousarray(np.asarray(series, dtype=float).T)
