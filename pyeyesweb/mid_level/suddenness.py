"""Suddenness evaluation based on velocity distribution."""

from typing import Any, Literal, Optional

from pyeyesweb._core import core
from pyeyesweb.base.core_feature import CoreFeature
from pyeyesweb.catalog import Layer, describe
from pyeyesweb.data_models.feature import WindowedFeature
from pyeyesweb.data_models.inputs import Input, InputKind, Inputs
from pyeyesweb.data_models.results import Output, Result, Schema, Status
from pyeyesweb.base.choices import coerce_enum
from pyeyesweb.base.inputs import InferredDims
from pyeyesweb.base.minimum_window import MinimumWindow


_ALGORITHMS = core.motion.SuddennessAlgorithm
_Algorithm = Literal["constrained", "quantile"]


class _SuddennessFit(MinimumWindow):
    """What the features that fit the velocity distribution share: the minimum window, the `(dims,)` point of the
    trajectory (`dims` = 2 or 3) and the `algorithm` parameter."""

    MIN_WINDOW = 6

    def _fit_result(self, fitted_alpha: float, timestamp: Optional[float], **values: Any) -> Result:
        """The `Result` of a fit; `INVALID_INPUT` (no numbers) when `fitted_alpha` is the core's -1 sentinel, the
        QUANTILE algorithm's way to say that the window is out of the table range."""
        if fitted_alpha == -1:
            return self.result(status=Status.INVALID_INPUT, reason="the distribution could not be fitted",
                               timestamp=timestamp, **values)
        return self.result(timestamp=timestamp, **values)

    def _inputs(self) -> Inputs:
        return Inputs(Input("position", InputKind.SAMPLE, (self.dims,), doc="(x, y) or (x, y, z) of the trajectory"))

    def _set_dims(self, value: Optional[int], inferred: bool) -> None:
        if value not in (None, 2, 3):
            raise ValueError(f"{type(self).__name__}: a position has 2 or 3 coordinates, got {value}")
        super()._set_dims(value, inferred)

    @property
    def algorithm(self) -> _Algorithm:
        return self._params["algorithm"].name.lower()

    @algorithm.setter
    def algorithm(self, value: Any):
        self._set_param("algorithm", coerce_enum(value, _ALGORITHMS, "algorithm"))


@describe(Layer.MID_LEVEL)
class Suddenness(_SuddennessFit, InferredDims, WindowedFeature, CoreFeature):
    """Suddenness evaluation based on velocity distribution.

    !!! note
        This method evaluates suddenness by modeling the velocity distribution as a stable distribution.

    Read more in the [User Guide](../../user_guide/theoretical_framework/mid_level/suddenness.md).

    Input: one position per call, the `(dims,)` point of a trajectory with `dims` = 2 or 3 coordinates (a
    `(signals, dims)` frame is rejected: average the markers before the call if one trajectory is wanted). The feature
    buffers `window` frames and computes every `hop` frames (`WARMING_UP` while the first window fills, `NO_OUTPUT`
    between hops). `_process_window(series)` computes one complete window directly: `series` is `(dims, window)`.
    `timestamp` is the timestamp, in seconds, of the newest frame.

    Parameters
    ----------
    window : int
        Frames per window.
    hop : int, optional
        New frames between two windows. Defaults to `1`.
    dims : int, optional
        Coordinates of the position, 2 or 3. Defaults to the size of the first position.
    algo : str, optional
        The algorithm to use for stable distribution fitting. Defaults to `"new"`.

    Returns
    -------
    Result
        `is_sudden` (bool) and the fitted stable-distribution parameters `alpha`, `beta`, `gamma` (float).
        `Status.WARMING_UP` while the window holds fewer than 6 frames.
    """

    OUTPUTS = Schema(
        Output("is_sudden", kind=bool, doc="Whether the movement is classified as sudden."),
        Output("alpha", doc="Stability parameter of the fitted stable distribution."),
        Output("beta", doc="Skewness parameter of the fitted stable distribution."),
        Output("gamma", doc="Scale parameter of the fitted stable distribution."),
    )

    _core_class = core.motion.Suddenness
    _lazy_block = True

    def __init__(self, window: int, hop: int = 1, dims: Optional[int] = None,
                 algorithm: _Algorithm = "constrained"):
        super().__init__(window=window, hop=hop)
        self.dims = dims
        self.algorithm = algorithm
        self._check_window()

    def _process_window(self, series: Any, *, timestamp: Optional[float] = None) -> Result:
        pos = self._window_trajectory(series)
        if (unusable := self._unusable(pos, timestamp)) is not None:
            return unusable

        alpha, beta, gamma, is_sudden = self._block.process(pos)
        return self._fit_result(alpha, timestamp, is_sudden=is_sudden, alpha=alpha, beta=beta, gamma=gamma)


__all__ = ["Suddenness"]
