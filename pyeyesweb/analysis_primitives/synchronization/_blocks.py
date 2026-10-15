"""Bases shared by the synchronization features.

Two kinds of feature:

* frame features (event detectors, counters, matrix transforms): stateful, run once per sample;
* `_SeriesBlock`: a `WindowedFeature` that buffers ``window`` samples per input and computes every ``hop`` samples,
  on one ``(channels, window)`` series per input.

Subclasses implement `_to_result(raw, timestamp)` (``timestamp`` is ``NaN`` when not given) and, where the feature does
not simply take one array per input, `_call_block(args)`.
"""

from typing import Any, Optional, Sequence

import numpy as np

from pyeyesweb.base.core_feature import CoreFeature
from pyeyesweb.base.inputs import non_finite, train
from pyeyesweb.base.minimum_window import MinimumWindow
from pyeyesweb.data_models.feature import WindowedFeature
from pyeyesweb.data_models.inputs import Input, InputKind
from pyeyesweb.data_models.results import Result, Status


def _train(name: str, doc: str = "event train, non-zero = event") -> Input:
    return Input(name, InputKind.SAMPLE, (1,), doc=doc)


class _SeriesBlock(MinimumWindow, WindowedFeature, CoreFeature):
    """A feature that runs on a buffered series; ``window`` and ``hop`` are the first constructor parameters.

    `_finite_inputs`: NaN / inf in a window gives ``INVALID_INPUT``. `_minimum_window(**params)`: the shortest window
    accepted with these parameters, checked at construction and whenever ``window`` or a parameter changes.
    """

    _finite_inputs = False

    def __init__(self, window: int, hop: int = 1, **params: Any):
        super().__init__(window, hop, **params)
        self._check_window()

    def _set_param(self, name: str, value: Any) -> None:
        self._check_window(**{name: value})
        super()._set_param(name, value)

    def _call_block(self, args: Sequence[Any]) -> Any:
        """Run the core block on the series of one call (one entry per declared input)."""
        return self._block.process(*args)

    def _to_result(self, raw: Any, timestamp: float) -> Result:
        raise NotImplementedError

    def _process_window(self, *series: Any, timestamp: Optional[float] = None) -> Result:
        arrays = [np.ascontiguousarray(signal, dtype=float) for signal in series]
        # NaN / inf in an input would turn into NaN outputs in the core
        if self._finite_inputs and (reason := non_finite(np.concatenate([array.ravel() for array in arrays]), allow_empty=True)):
            return self._no_output(Status.INVALID_INPUT, reason, timestamp)
        return self._to_result(self._call_block(arrays), timestamp)


class _TrainPairBlock(_SeriesBlock):
    """A series block with two one-channel inputs, which the core takes as 1-D arrays."""

    def _call_block(self, args: Sequence[Any]) -> Any:
        return self._block.process(*(train(argument) for argument in args))
