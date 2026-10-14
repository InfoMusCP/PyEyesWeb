"""Rarity of the newest value of a signal, with two methods.

This module implements the [Rarity][pyeyesweb.analysis_primitives.rarity.Rarity] feature: how typical or atypical the
current state is relative to a memory of past states. The formula is chosen by `method`.
"""

from typing import Any, Literal, Optional

import numpy as np

from pyeyesweb._core import core
from pyeyesweb.base.inputs import non_finite
from pyeyesweb.base.core_feature import CoreFeature, FrameFeature, VariantFeature
from pyeyesweb.base.minimum_window import MinimumWindow
from pyeyesweb.catalog import Layer, describe
from pyeyesweb.data_models.feature import WindowedFeature
from pyeyesweb.data_models.inputs import Input, InputKind, Inputs
from pyeyesweb.data_models.results import Output, Result, Schema, Status
from pyeyesweb.utils.validators import validate_numeric


@describe(Layer.ANALYSIS_PRIMITIVE, eyesweb="rarityindex (Rarity)")
class Rarity(VariantFeature, CoreFeature):
    r"""Rarity of the newest value of a signal within a memory of past values, by `method`.

    The two methods are different formulas (neither is a special case of the other); the parameters, inputs and
    outputs are those of the chosen method, and a parameter of the other method raises an error.

    `"information"` (default): the port of the EyesWeb `rarityindex` block. Each of `number_of_inputs`
    scalar signals is discretised into bins of user-given widths; the block keeps its own memory and computes a
    Contrast across the inputs or a Rarity across the last values of the same input (parameter `RarityType`, see
    the core block for the other parameters). Input: one sample of `number_of_inputs` values per call
    (`process(*sample, timestamp=None)`). Output `rarity`, shape `(number_of_inputs,)` (default 2): one index per input,
    $-\log(A B + 10^{-16})$; `timestamp` is the timestamp in seconds (`NaN` when not given). `reset()` clears the memory
    and the bin indices, so `run` is a pure function of the recording. Status: with `type="rarity"` the memory starts
    filled with zeros, so the outputs are `WARMING_UP` (the numbers are given, but are artefacts) until `data_memory`
    samples have been seen; a value above the sum of the bin widths keeps the previous bin and gives
    `INVALID_INPUT` ("value outside the bins"), with no numbers; `NaN` or infinity is `INVALID_INPUT` before the block sees
    it. `type="contrast"` needs at least 2 inputs and
    `type="rarity"` a `data_memory` of at least 2: otherwise construction raises `ValueError`.

    `"mode_distance"`: windowed rarity of a scalar stream. Parameters `window`, `hop` (default 1) and
    `alpha` (default 0.5). Input: one value per call, buffered over `window` samples and computed every `hop`
    samples (`WARMING_UP` while the first window fills, `NO_OUTPUT` between hops); `_process_window(series)` takes
    one `(1, window)` window. The histogram of the window has $\max(\lfloor\sqrt{N}\rfloor, 1)$ equal-width bins
    and the score is $|\mathrm{mode} - \mathrm{last}| (p_\mathrm{mode} - p_\mathrm{last}) \alpha$. Output `rarity`
    (float, $\ge 0$): higher means more atypical; `WARMING_UP` below 2 samples, `INVALID_INPUT` when the window holds a NaN or an infinite value (it stays invalid until that sample leaves the window). The maths runs in the compiled core.

    Use `"information"` to reproduce EyesWeb or to compare several signals with chosen bin widths; use
    `"mode_distance"` for a self-contained score of one stream that needs no bin widths.

    Read more in the [User Guide](../../user_guide/theoretical_framework/analysis_primitives/rarity.md).

    Parameters
    ----------
    method : {"information", "mode_distance"}, optional
        Formula. Defaults to `"information"`.
    **params
        Parameters of the chosen method.

    Examples
    --------
    >>> rarity = Rarity(method="mode_distance", window=100, alpha=1.0)
    """

    _SWITCH = ("method", "information")
    _variants = {}

    @property
    def method(self) -> Literal["information", "mode_distance"]:
        return self._variant


class _ModeDistanceRarity(MinimumWindow, WindowedFeature, Rarity, variant="mode_distance"):
    r"""Rarity of the latest sample relative to the window distribution (method `"mode_distance"`).

    Input: one value per call. The feature buffers `window` samples and computes every `hop` samples (`process`
    returns `WARMING_UP` while the first window fills and `NO_OUTPUT` between hops); `_process_window(series)` takes
    one complete `(1, window)` window. `timestamp` is the timestamp (seconds) of the newest sample.

    The number of histogram bins is $\max(\lfloor\sqrt{N}\rfloor, 1)$ where $N$ is the number of samples. Rarity
    compares the probability of the most recent sample with that of the most probable bin. The maths runs in the
    compiled core (`core.motion.HistogramRarity`).

    Parameters
    ----------
    window : int
        Samples per window.
    hop : int, optional
        New samples between two windows. Defaults to `1`.
    alpha : float, optional
        Scaling factor for the rarity calculation. Defaults to `0.5`.
    """

    OUTPUTS = Schema(Output("rarity", doc="Rarity score >= 0; higher values indicate more atypical movement."))

    _core_class = core.motion.HistogramRarity
    _lazy_block = True

    def __init__(self, window: int, hop: int = 1, alpha: float = 0.5, *,
                 method: str = "mode_distance"):
        super().__init__(window=window, hop=hop)
        self._check_window()
        self.alpha = alpha

    def _minimum_window(self) -> int:
        return 2

    @property
    def alpha(self) -> float:
        """Scaling factor for rarity."""
        return self._params["alpha"]

    @alpha.setter
    def alpha(self, value: float):
        if validate_numeric(value, "alpha") <= 0:
            raise ValueError(f"alpha must be > 0, got {value}")
        self._set_param("alpha", float(value))

    def _inputs(self) -> Inputs:
        return Inputs(Input("signal", InputKind.SAMPLE, (1,), doc="one value per call"))

    def _process_window(self, series: Any, *, timestamp: Optional[float] = None) -> Result:
        """Compute rarity of the newest sample of a window within the window distribution.

        `series` is one complete window, `(1, window)`, the newest sample last (flattened to 1-D); `timestamp` is the
        timestamp of the window (seconds). `Status.WARMING_UP` when fewer than 2 samples are present.
        """
        samples = np.ascontiguousarray(series, dtype=float).ravel()
        if len(samples) < 2:
            return self.no_output(Status.WARMING_UP, "fewer than 2 samples", timestamp)
        if reason := non_finite(samples):
            return self.no_output(Status.INVALID_INPUT, reason, timestamp)
        return self.result(rarity=self._block.process(samples), timestamp=timestamp)


class _InformationRarity(Rarity, FrameFeature, variant="information"):
    """EyesWeb Rarity (rarity or contrast) of `number_of_inputs` scalar signals (method `"information"`).

    Input: one sample of `number_of_inputs` values per call; the block keeps its own memory of past samples
    (`process(*sample, timestamp=None)`, `reset()` clears it and the bin indices, so `run` is a pure function of the recording).

    Output `rarity`, shape `(number_of_inputs,)` (constructor parameter, default 2): one index per input,
    -log(A * B + 1e-16); `timestamp` is the timestamp in seconds (`NaN` when not given). `WARMING_UP` while the memory of
    `type="rarity"` is not full yet, `INVALID_INPUT` ("value outside the bins") for a value above the sum of the bins.
    """
    _core_class = core.motion.RarityIndex
    _filled = 0  # samples written to the memory since it was last empty (type "rarity" only)

    def reset(self) -> None:
        super().reset()
        self._filled = 0

    def _state_lost(self) -> None:
        super()._state_lost()
        self._filled = 0

    def __init__(self, *, method: str = "information", **params: Any):
        super().__init__(**params)

    def _number_of_inputs(self) -> int:
        return int(self._param("number_of_inputs", 2))  # C++ default

    def _inputs(self) -> Inputs:
        return Inputs(Input("signals", InputKind.SAMPLE, (self._number_of_inputs(),), doc="one value per signal"))

    def _schema(self) -> Schema:
        return Schema(Output("rarity", self._number_of_inputs(), doc="-log(A * B + 1e-16) for each input"))

    def _process(self, sample: Any, timestamp: Optional[float]) -> Result:
        values = np.asarray(sample, dtype=float).ravel()
        rarity = np.asarray(self._block.process(values), dtype=float)
        memory = int(self._param("data_memory", 50))  # C++ defaults
        uses_memory = self._param("type", core.motion.RarityType.RARITY) == core.motion.RarityType.RARITY
        self._filled += uses_memory
        if not np.all(values <= np.cumsum(self._param("bins", [0.3, 0.3, 0.4]))[-1]):  # also NaN
            return self.result(status=Status.INVALID_INPUT, reason="value outside the bins", rarity=rarity, timestamp=timestamp)
        if uses_memory and self._filled < memory:
            return self.result(status=Status.WARMING_UP, reason=f"the memory holds {self._filled} of {memory} values",
                               rarity=rarity, timestamp=timestamp)
        return self.result(rarity=rarity, timestamp=timestamp)

for _variant in (_ModeDistanceRarity, _InformationRarity):
    _variant.__name__ = Rarity.__name__


__all__ = ["Rarity"]
