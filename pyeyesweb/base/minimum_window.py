"""The check shared by the windowed features whose core needs a minimum number of samples per window."""

from typing import Optional

import numpy as np

from pyeyesweb.base.inputs import non_finite
from pyeyesweb.data_models.results import Result, Status


class MinimumWindow:
    """Mixin placed before `WindowedFeature`: `window` must be at least `_minimum_window()`.

    A feature sets the constant `MIN_WINDOW`, or overrides `_minimum_window(**params)` (the parameters given override
    the current ones), and calls `_check_window()` at the end of its constructor and `_check_window(name=value)` in
    the setter of a parameter the minimum depends on. Setting `window` is checked here. `_minimum_reason(**params)` says
    where the minimum comes from, when it is not obvious, and ends up in the error.
    """

    MIN_WINDOW = 1

    def _minimum_window(self, **params: int) -> int:
        return self.MIN_WINDOW

    def _minimum_reason(self, **params: int) -> str:
        return ""

    def _check_window(self, window: Optional[int] = None, **params: int) -> None:
        window = self._window if window is None else int(window)
        minimum = self._minimum_window(**params)
        if window < minimum:
            raise ValueError(f"{type(self).__name__}: window must be >= {minimum}{self._minimum_reason(**params)} (got {window})")

    def configure(self, window: Optional[int] = None, hop: Optional[int] = None) -> None:
        if window is not None:
            self._check_window(window)
        super().configure(window, hop)

    def _unusable(self, data: np.ndarray, timestamp: Optional[float]) -> Optional[Result]:
        """`WARMING_UP` when `data` (frames first) is shorter than the minimum, `INVALID_INPUT` when not finite."""
        if len(data) < (minimum := self._minimum_window()):
            return self._no_output(Status.WARMING_UP, f"fewer than {minimum} frames", timestamp)
        if reason := non_finite(data, allow_empty=True):
            return self._no_output(Status.INVALID_INPUT, reason, timestamp)
        return None
