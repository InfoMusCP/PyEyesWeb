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
    r"""Direction change of a trajectory in a window: sharp turns of the path and the area it encloses.

    The feature looks at the path of a point (a joint, a marker, the centre of mass) over a window of ``window``
    positions and gives up to two measures, selected with ``metrics``.

    **Cosine metric.** It looks for a turn of about a right angle between the first half and the second half of the
    path. With :math:`\mathbf{p}_0` the oldest, :math:`\mathbf{p}_m` the middle and :math:`\mathbf{p}_N` the newest
    position of the window, :math:`\mathbf{l}_1 = \mathbf{p}_m - \mathbf{p}_0` and
    :math:`\mathbf{l}_2 = \mathbf{p}_N - \mathbf{p}_m`, the angle between the two segments is
    :math:`\theta = \arccos\frac{\mathbf{l}_1\cdot\mathbf{l}_2}{\lVert\mathbf{l}_1\rVert\,\lVert\mathbf{l}_2\rVert}`,
    :math:`a = 1 - \theta/\pi`, and

    .. math::

        D_{\cos} = \begin{cases} 1 - \dfrac{|a - 0.5|}{\epsilon} & |a - 0.5| < \epsilon, \\
        0 & \text{otherwise,} \end{cases}

    so that :math:`D_{\cos}` is 1 for a right-angle turn (:math:`\theta = 90^\circ`) and falls to 0 at a distance
    ``epsilon`` from it; a straight path or a U-turn gives 0.

    **Polygon metric.** The positions are subsampled to ``number_of_subsamples`` points and the feature returns the
    area of the polygon they form, the shoelace sum of cross products :math:`\tfrac12\lVert\sum_i \mathbf{X}_i\times
    \mathbf{X}_{i+1}\rVert`, in the unit of the data squared: large for broad, sweeping movements that enclose space,
    small for narrow or linear ones (a path that winds several times counts its area several times).

    Parameters
    ----------
    window : int
        Frames per window (at least 3). Changing it on a running feature keeps the newest frames.
    hop : int, optional
        New frames between two windows. Defaults to ``1``.
    epsilon : float, optional
        Half-width, in units of :math:`a` (dimensionless), of the interval around a right angle in which the cosine
        metric is non-zero. Defaults to ``0.5``. *(live)*
    number_of_subsamples : int, optional
        Number of points the window is subsampled to for the polygon area. Defaults to ``20``. *(live)*
    metrics : list of {"cosine", "polygon"}, optional
        The metrics to compute, one output each. By default both. *(live)*

    Notes
    -----
    **Inputs.** One position per call, ``process(position, *, timestamp=None)``: the ``(D,)`` point of a trajectory,
    ``D`` = 2 or 3 (any other ``D`` raises ``ValueError``); ``run(positions, *, timestamps=None)`` takes a ``(T, D)``
    recording. A ``(signals, D)`` frame or a dict is rejected: average the markers before the call if one trajectory
    is wanted. ``timestamp`` and ``timestamps`` are in seconds.

    **Outputs.** ``cosine`` (dimensionless, in [0, 1]) and ``polygon`` (length squared, 0 or more), those requested in
    ``metrics``; ``feature.outputs`` lists exactly them.

    **Statuses.** ``WARMING_UP`` while the first window fills (``"k of N samples"``), ``NO_OUTPUT`` between two
    windows when ``hop > 1``, ``INVALID_INPUT`` for unusable data (a non-finite sample, for example).

    Corrected in the core: the feature takes one trajectory. It used to take the mean of all the markers of a frame
    as its trajectory, a hidden reduction; it now rejects a frame with several markers. The numbers for a single
    point are unchanged.

    Examples
    --------
    >>> import numpy as np
    >>> from pyeyesweb.low_level import DirectionChange
    >>> out = np.c_[np.arange(11.0), np.zeros(11)]  # 10 steps along x ...
    >>> up = np.c_[10.0 * np.ones(10), np.arange(1.0, 11.0)]  # ... then 10 steps along y
    >>> feature = DirectionChange(window=21)
    >>> result = feature.run(np.vstack([out, up]))[-1]
    >>> round(float(result.cosine), 2), round(float(result.polygon), 1)
    (1.0, 49.5)
    """

    _OUTPUTS = Schema(
        Output("cosine", doc="Direction change from the cosine similarity of the start-mid-end vectors, in [0, 1]."),
        Output("polygon", unit="<length>^2", doc="Area of the polygon enclosed by the subsampled trajectory."),
    )

    _ALLOWED_METRICS = ["cosine", "polygon"]
    _core_class = core.motion.DirectionChange
    _core_names = {"number_of_subsamples": "num_subsamples"}
    _lazy_block = True

    def _schema(self) -> Schema:
        return self._OUTPUTS.select(self.metrics)

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
        """Direction change of one complete ``(D, window)`` series; see the class documentation."""
        series = np.asarray(series, dtype=float)
        if series.shape[-1] < 3:
            return self._no_output(Status.WARMING_UP, "fewer than 3 samples", timestamp)
        if reason := non_finite(series, allow_empty=True):
            return self._no_output(Status.INVALID_INPUT, reason, timestamp)

        engine = self._block
        values = {}

        try:
            trajectory = np.ascontiguousarray(series.T)
            if "cosine" in self.metrics:
                values["cosine"] = engine.cosine(trajectory)

            if "polygon" in self.metrics:
                values["polygon"] = engine.polygon_area(trajectory)

        except ValueError as exc:
            return self._no_output(Status.INVALID_INPUT, str(exc), timestamp)

        return self._finite_result(timestamp=timestamp, **values)


__all__ = ['DirectionChange']
