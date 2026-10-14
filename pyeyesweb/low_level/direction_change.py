from typing import Any, Literal, List, Optional
import numpy as np

from pyeyesweb.catalog import Layer, describe
from pyeyesweb.data_models.feature import WindowedFeature
from pyeyesweb.base.inputs import non_finite
from pyeyesweb.data_models.inputs import Input, InputKind, Inputs
from pyeyesweb.data_models.results import Output, Result, Schema, Status
from pyeyesweb._core import core
from pyeyesweb.base.core_feature import CoreFeature
from pyeyesweb.base.minimum_window import MinimumWindow
from pyeyesweb.utils.validators import validate_string


@describe(Layer.LOW_LEVEL)
class DirectionChange(MinimumWindow, WindowedFeature, CoreFeature):
    """Direction Change evaluation based on movement vectors (maths in the compiled core).

    !!! note
        Supports multiple metrics such as cosine similarity and polygon area.

    Read more in the [User Guide](../../user_guide/theoretical_framework/low_level/direction_change.md).

    Input: one position per call, the `(D,)` point of a trajectory with `D` = 2 or 3 coordinates (any other `D`
    raises `ValueError`); `run` takes a `(T, D)` recording. A `(signals, D)` frame or a dict is rejected: average the
    markers before the call if one trajectory is wanted. The feature buffers `window` positions and computes every
    `hop` frames (`WARMING_UP` while the first window fills, `NO_OUTPUT` between hops); the buffer holds the `D`
    coordinates and `_process_window(series)` takes one complete `(D, window)` series. `timestamp` and `timestamps`
    are in seconds.

    Parameters
    ----------
    window : int
        Frames per window (at least 3).
    hop : int, optional
        New frames between two windows. Defaults to `1`.
    epsilon : float, optional
        Threshold parameter for the cosine metric. Defaults to `0.5`.
    number_of_subsamples : int, optional
        Number of subsamples used for polygon area calculation. Defaults to `20`.
    metrics : list of {'cosine', 'polygon'}, optional
        The metrics to compute. By default, computes all allowed metrics.

    Returns
    -------
    Result
        One scalar output per requested metric: `cosine` (direction change by cosine similarity) and/or
        `polygon` (area enclosed by the trajectory); `feature.outputs` lists exactly the requested ones.
        `Status.WARMING_UP` below 3 samples, `Status.INVALID_INPUT` for unusable data.
    """

    OUTPUTS = Schema(
        Output("cosine", doc="Direction change from the cosine similarity of the start-mid-end vectors, in [0, 1]."),
        Output("polygon", doc="Area of the polygon enclosed by the subsampled trajectory."),
    )

    _ALLOWED_METRICS = ["cosine", "polygon"]
    _core_class = core.motion.DirectionChange
    _core_names = {"number_of_subsamples": "num_subsamples"}
    _lazy_block = True

    def _schema(self) -> Schema:
        return self.OUTPUTS.select(self.metrics)

    def _inputs(self) -> Inputs:
        return Inputs(Input("position", InputKind.SAMPLE, (None,), doc="(x, y) or (x, y, z) of the trajectory"))

    def _minimum_window(self) -> int:
        return 3

    def __init__(
            self,
            window: int,
            hop: int = 1,
            *,
            epsilon: float = 0.5,
            number_of_subsamples: int = 20,
            metrics: Optional[List[Literal["cosine", "polygon"]]] = None
    ):
        super().__init__(window=window, hop=hop)
        self._check_window()
        self.epsilon = epsilon
        self.number_of_subsamples = number_of_subsamples
        self.metrics = metrics

    @property
    def epsilon(self) -> float:
        return self._params["epsilon"]

    @epsilon.setter
    def epsilon(self, value: float):
        self._set_param("epsilon", float(value))

    @property
    def number_of_subsamples(self) -> int:
        return self._params["number_of_subsamples"]

    @number_of_subsamples.setter
    def number_of_subsamples(self, value: int):
        self._set_param("number_of_subsamples", int(value))

    @property
    def metrics(self) -> List[str]:
        return self._metrics

    @metrics.setter
    def metrics(self, value: Optional[List[str]]):
        target_metrics = value if value is not None else self._ALLOWED_METRICS
        self._metrics = [validate_string(metric, self._ALLOWED_METRICS) for metric in target_metrics]

    def _check_dimension(self, position: Any) -> None:
        if (size := np.size(position)) not in (0, 2, 3):
            raise ValueError(f"DirectionChange: a position has 2 or 3 coordinates, got {size}")

    def process(self, position: Any, *, timestamp: Optional[float] = None) -> Result:
        self._check_dimension(position)
        return super().process(position, timestamp=timestamp)

    def _check_recording(self, arrays: Any) -> None:
        super()._check_recording(arrays)
        if len(arrays[0]):
            self._check_dimension(arrays[0][0])

    def _process_window(self, series: Any, *, timestamp: Optional[float] = None) -> Result:
        """Direction change of one complete `(D, window)` series; see the class documentation."""
        series = np.asarray(series, dtype=float)
        if series.shape[-1] < 3:
            return self.no_output(Status.WARMING_UP, "fewer than 3 samples", timestamp)
        if reason := non_finite(series, allow_empty=True):
            return self.no_output(Status.INVALID_INPUT, reason, timestamp)

        engine = self._block
        values = {}

        try:
            trajectory = np.ascontiguousarray(series.T)
            if "cosine" in self.metrics:
                values["cosine"] = engine.cosine(trajectory)

            if "polygon" in self.metrics:
                values["polygon"] = engine.polygon_area(trajectory)

        except ValueError as exc:
            return self.no_output(Status.INVALID_INPUT, str(exc), timestamp)

        return self.finite_result(timestamp=timestamp, **values)


__all__ = ['DirectionChange']
