"""Periodicity of a signal (EyesWeb PeriodicityIndex)."""

from typing import Any, Optional

import numpy as np

from pyeyesweb._core import core
from pyeyesweb.base.core_feature import CoreFeature
from pyeyesweb.base.minimum_window import MinimumWindow
from pyeyesweb.catalog import Layer, describe
from pyeyesweb.data_models.feature import WindowedFeature
from pyeyesweb.data_models.inputs import Input, InputKind, Inputs
from pyeyesweb.data_models.results import Output, Result, Schema


@describe(Layer.ANALYSIS_PRIMITIVE, eyesweb="PeriodicityIndex (Periodicity)")
class Periodicity(MinimumWindow, WindowedFeature, CoreFeature):
    """Periodicity Transform of each channel of a window (EyesWeb Periodicity).

    Input: samples of `C` channels, one per call. The feature buffers `window` samples and computes every `hop`
    samples (`process` returns `WARMING_UP` while the first window fills and `NO_OUTPUT` between hops).
    `_process_window(series)` computes one complete `(C, window)` window directly, which is the EyesWeb Execute.
    `sampling_rate` (Hz) is passed to the block as EyesWeb's static series sampling rate (0 = unknown).

    Outputs `periods` and `powers`, both `(channels, columns)` arrays (data-dependent size, so not part of
    `to_array()`): entry k of channel c is a detected period (samples) and its normalised power. Unused entries
    are -1, as in EyesWeb. `OK` whenever a window was computed.
    """
    _core_class = core.motion.PeriodicityIndex
    _core_names = {"method": "algorithm"}

    def __init__(self, window: int, hop: int = 1, **params: Any):
        super().__init__(window=window, hop=hop, **params)
        self._check_window()

    def _minimum_window(self) -> int:
        return 2

    def _inputs(self) -> Inputs:
        return Inputs(Input("signal", InputKind.SAMPLE, (None,), doc="one value per channel"))

    def _schema(self) -> Schema:
        return Schema(Output("periods", (None, None), unit="samples", doc="detected periods in samples, -1 = unused"),
                      Output("powers", (None, None), doc="normalised power of each period, -1 = unused"))

    def _process_window(self, series: Any, *, timestamp: Optional[float] = None) -> Result:
        raw = self._block.process(np.asarray(series, dtype=float), 0.0)
        return self._result(periods=raw[0::2], powers=raw[1::2], timestamp=timestamp)


__all__ = ["Periodicity"]
