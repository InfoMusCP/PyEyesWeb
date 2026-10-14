"""Complexity of a signal: sample entropy, coarse graining (EyesWeb MotionAnalysis).

Both blocks run on a static series in EyesWeb, so they are windowed features: `process(sample)` fills a window of
`window` samples and computes every `hop` samples, `_process_window(series)` is the EyesWeb Execute on one complete
`(channels, window)` series.
"""

from typing import Any, Optional

import numpy as np

from pyeyesweb._core import core
from pyeyesweb.base.core_feature import CoreFeature
from pyeyesweb.base.minimum_window import MinimumWindow
from pyeyesweb.catalog import Layer, describe
from pyeyesweb.data_models.feature import WindowedFeature
from pyeyesweb.data_models.inputs import Input, InputKind, Inputs
from pyeyesweb.data_models.results import Output, Result, Schema, Status

_motion = core.motion


@describe(Layer.ANALYSIS_PRIMITIVE, eyesweb="sampleentropy")
class SampleEntropy(MinimumWindow, WindowedFeature, CoreFeature):
    """EyesWeb SampleEntropy of a single-channel window.

    Input: one value per call. `window` and `hop` as in `WindowedFeature`; `_process_window(series)` takes one
    complete `(1, window)` series. `tolerance` (default `None`) is the absolute matching tolerance in the units of the signal; `None`
    means `relative_tolerance * std(window)` with `relative_tolerance=0.2` (population standard deviation of the window;
    `1e-6` for a constant window), where EyesWeb has an absolute 0.3. Both are live parameters.

    Output `sample_entropy`, shape `(embedding_dimension,)` (constructor parameter, default 12): entry k = -log(A[k] / B[k]) for
    template length k + 1. `OK` whenever a window was computed; `timestamp` is the timestamp (seconds) of the newest sample.
    """
    _core_class = _motion.SampleEntropy

    def __init__(self, window: int, hop: int = 1, **params: Any):
        super().__init__(window=window, hop=hop, **params)
        self._check_window()

    @property
    def embedding_dimension(self) -> int:
        return int(self._param("embedding_dimension", 12))  # C++ default

    @embedding_dimension.setter
    def embedding_dimension(self, value: int) -> None:
        self._check_window(embedding_dimension=value)
        self._set_param("embedding_dimension", value)

    @property
    def tolerance(self) -> Optional[float]:
        return self._param("tolerance", None)  # C++ default

    @tolerance.setter
    def tolerance(self, value: Optional[float]) -> None:
        self._set_param("tolerance", value)

    @property
    def relative_tolerance(self) -> float:
        return float(self._param("relative_tolerance", 0.2))  # C++ default

    @relative_tolerance.setter
    def relative_tolerance(self, value: float) -> None:
        self._set_param("relative_tolerance", value)

    def _minimum_window(self, **params: int) -> int:
        return int(params.get("embedding_dimension", self.embedding_dimension)) + 1

    def _inputs(self) -> Inputs:
        return Inputs(Input("signal", InputKind.SAMPLE, (1,), doc="one value per call"))

    def _schema(self) -> Schema:
        return Schema(Output("sample_entropy", self.embedding_dimension, doc="-log(A[k] / B[k]) for template length k + 1"))

    def _process_window(self, series: Any, *, timestamp: Optional[float] = None) -> Result:
        raw = self._block.process(np.asarray(series, dtype=float))
        return self.result(sample_entropy=raw[0], timestamp=timestamp)


@describe(Layer.ANALYSIS_PRIMITIVE, eyesweb="coarsegraining")
class CoarseGraining(MinimumWindow, WindowedFeature, CoreFeature):
    """EyesWeb CoarseGraining of a window of `C` channels.

    Input: one sample of `C` values per call. `window` and `hop` as in `WindowedFeature`; `_process_window(series)`
    takes one complete `(C, window)` series. The other parameters (`factor`, ...) are those of the EyesWeb block.

    Output `coarse_grained`: `(channels, window // factor)` coarse-grained series (data-dependent size). `NO_OUTPUT`
    (`coarse_grained` not produced) on the windows where EyesWeb does not recompute it, as well as between hops.
    """
    _core_class = _motion.CoarseGraining

    def __init__(self, window: int, hop: int = 1, **params: Any):
        super().__init__(window=window, hop=hop, **params)
        self._check_window()

    @property
    def factor(self) -> int:
        return int(self._param("factor", 2))  # C++ default

    @factor.setter
    def factor(self, value: int) -> None:
        self._check_window(factor=value)
        self._set_param("factor", value)

    def _minimum_window(self, **params: int) -> int:
        return int(params.get("factor", self.factor))

    def _inputs(self) -> Inputs:
        return Inputs(Input("signal", InputKind.SAMPLE, (None,), doc="one value per channel"))

    def _schema(self) -> Schema:
        return Schema(Output("coarse_grained", (None, None), doc="coarse-grained series (channels, window // factor)"))

    def _process_window(self, series: Any, *, timestamp: Optional[float] = None) -> Result:
        raw = self._block.process(np.asarray(series, dtype=float))
        if raw is None:
            return self.no_output(Status.NO_OUTPUT, "not recomputed on this activation", timestamp)
        return self.result(coarse_grained=raw, timestamp=timestamp)


__all__ = ["SampleEntropy", "CoarseGraining"]
