"""Impulsivity analysis for body movement patterns."""

from typing import Any, Optional

from pyeyesweb._core import core
from pyeyesweb.base.core_feature import CoreFeature
from pyeyesweb.catalog import Layer, describe
from pyeyesweb.data_models.feature import WindowedFeature
from pyeyesweb.data_models.inputs import Input, InputKind, Inputs
from pyeyesweb.data_models.results import Output, Result, Schema
from pyeyesweb.base.inputs import InferredDims, scalar
from pyeyesweb.mid_level.suddenness import _Algorithm, _SuddennessFit


@describe(Layer.MID_LEVEL)
class SuddennessImpulsivity(_SuddennessFit, InferredDims, WindowedFeature, CoreFeature):
    """Impulsivity evaluation based on the product of Direction Change and Suddenness.

    The maths runs in the compiled core (`core.motion.SuddennessImpulsivity`, composing the
    DirectionChange and Suddenness; the two are not outputs, run them for the intermediate values). Both evaluate the
    same single trajectory.

    Read more in the [User Guide](../../user_guide/theoretical_framework/mid_level/impulsivity.md).

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
    direction_change_epsilon : float, optional
        Epsilon threshold for Direction Change. Defaults to `0.5`.
    suddenness_algo : str, optional
        Algorithm to use for Suddenness. Defaults to `"new"`.

    Returns
    -------
    Result
        `impulsivity_index` (float). `INVALID_INPUT` ("the distribution could not be fitted", the index kept) when the
        `"quantile"` algorithm cannot fit the window, as in `Suddenness`; `WARMING_UP` below 6 frames.
    """

    OUTPUTS = Schema(
        Output("impulsivity_index", doc="Direction change times suddenness (0 when not sudden)."),
    )

    _core_class = core.motion.SuddennessImpulsivity
    _lazy_block = True

    def __init__(self, window: int, hop: int = 1, dims: Optional[int] = None, direction_change_epsilon: float = 0.5,
                 algorithm: _Algorithm = "constrained"):
        super().__init__(window=window, hop=hop)
        self.dims = dims
        self.direction_change_epsilon = direction_change_epsilon
        self.algorithm = algorithm
        self._check_window()

    @property
    def direction_change_epsilon(self) -> float:
        return self._params["direction_change_epsilon"]

    @direction_change_epsilon.setter
    def direction_change_epsilon(self, value: float):
        self._set_param("direction_change_epsilon", float(value))

    def _process_window(self, series: Any, *, timestamp: Optional[float] = None) -> Result:
        trajectory = self._window_trajectory(series)
        if (unusable := self._unusable(trajectory, timestamp)) is not None:
            return unusable
        impulsivity, alpha = self._block.process(trajectory)
        return self._fit_result(alpha, timestamp, impulsivity_index=impulsivity)


@describe(Layer.MID_LEVEL, eyesweb="Impulsivity")
class ContractionImpulsivity(CoreFeature):
    """EyesWeb Impulsivity (ImpulsivityIndex): the change of the contraction index over a short, energetic gesture.

    Two inputs, in call order: `sqom` (quantity of motion) and `ci` (contraction index), scalar samples
    (`process(sqom, ci, timestamp=None)`, `run(sqoms, cis, timestamps=None)`). Stateful.

    Outputs `impulsivity_index` (contraction-index change per second) and `gesture_duration` (frames): both 0
    except on the frame that closes an impulsive gesture. Always `OK`; `timestamp` is the timestamp in seconds.

    A gesture is a run of frames with `sqom` above `motion_threshold` (EyesWeb hard codes 0.01), closed by the first
    frame at or below it; it is impulsive when it lasts at most `ges_dur` frames and its peak `sqom` reaches
    `peak_threshold`. `frames` is the frame rate.
    """
    _core_class = core.motion.ImpulsivityIndex

    def _inputs(self) -> Inputs:
        return Inputs(Input("sqom", InputKind.SAMPLE, (1,), doc="quantity of motion"),
                      Input("ci", InputKind.SAMPLE, (1,), doc="contraction index"))

    def _schema(self) -> Schema:
        return Schema(Output("impulsivity_index", doc="contraction-index change per second"),
                      Output("gesture_duration", unit="frames"))

    def process(self, sqom: Any, ci: Any, *, timestamp: Optional[float] = None) -> Result:
        return self._to_result(self._block.process(scalar(sqom), scalar(ci)), timestamp)

    def _to_result(self, raw: Any, timestamp: Optional[float]) -> Result:
        index, duration = raw
        return self.result(impulsivity_index=index, gesture_duration=duration, timestamp=timestamp)


__all__ = ["SuddennessImpulsivity", "ContractionImpulsivity"]
