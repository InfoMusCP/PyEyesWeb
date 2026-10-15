"""Suddenness of a trajectory from the distribution of its speeds.
"""

from typing import Any, Literal, Optional

from pyeyesweb._core import core
from pyeyesweb.base.core_feature import CoreFeature
from pyeyesweb.catalog import Layer, describe
from pyeyesweb.data_models.feature import WindowedFeature
from pyeyesweb.data_models.inputs import Input, InputKind, Inputs
from pyeyesweb.data_models.results import Output, Result, Schema, Status
from pyeyesweb.base.choices import choice_name, coerce_enum
from pyeyesweb.base.inputs import InferredDims
from pyeyesweb.base.minimum_window import MinimumWindow


_ALGORITHMS = core.motion.SuddennessAlgorithm
_Algorithm = Literal["constrained", "quantile"]


class _SuddennessFit(MinimumWindow):
    """What the features that fit the velocity distribution share: the minimum window, the `(dims,)` point of the
    trajectory (`dims` = 2 or 3) and the `method` parameter."""

    MIN_WINDOW = 6

    def _fit_result(self, fitted_alpha: float, timestamp: Optional[float], **values: Any) -> Result:
        """The `Result` of a fit; `INVALID_INPUT` (no numbers) when `fitted_alpha` is the core's -1 sentinel, the
        QUANTILE algorithm's way to say that the window is out of the table range."""
        if fitted_alpha == -1:
            return self._result(status=Status.INVALID_INPUT, reason="the distribution could not be fitted",
                               timestamp=timestamp, **values)
        return self._result(timestamp=timestamp, **values)

    def _inputs(self) -> Inputs:
        return Inputs(Input("position", InputKind.SAMPLE, (self.dims,), doc="(x, y) or (x, y, z) of the trajectory"))

    def _set_dims(self, value: Optional[int], inferred: bool) -> None:
        if value not in (None, 2, 3):
            raise ValueError(f"{type(self).__name__}: a position has 2 or 3 coordinates, got {value}")
        super()._set_dims(value, inferred)

    @property
    def method(self) -> _Algorithm:
        return choice_name(self._params["method"])

    @method.setter
    def method(self, value: Any):
        self._set_param("method", coerce_enum(value, _ALGORITHMS, "method"))


@describe(Layer.MID_LEVEL)
class Suddenness(_SuddennessFit, InferredDims, WindowedFeature, CoreFeature):
    r"""Suddenness of a trajectory from a stable-distribution fit of its speed distribution.

    Measures whether a movement is made of sudden starts and stops. The speed of the trajectory between consecutive
    samples, :math:`v_t = \lVert x_{t+1} - x_t \rVert`, is taken over a window and its distribution is fitted with an
    :math:`\alpha`-stable distribution by McCulloch's method, from the quantiles :math:`x_5, x_{25}, x_{50}, x_{75},
    x_{95}` of the speeds:

    .. math::

        \nu_\alpha = \frac{x_{95} - x_5}{x_{75} - x_{25}}, \qquad
        \nu_\beta = \frac{x_{95} + x_5 - 2 x_{50}}{x_{95} - x_5}, \qquad
        \gamma = \frac{x_{75} - x_{25}}{x_{75} - x_{50}},

    where :math:`\alpha \in (0, 2]` (stability, thickness of the tails: 2 for a Gaussian, towards 0 for heavy tails) and
    :math:`\beta \in [-1, 1]` (skewness) are obtained from :math:`\nu_\alpha` and :math:`\nu_\beta` by interpolation in
    McCulloch's tables. The window is classified as sudden when

    .. math::

        \gamma \left(1 - \frac{\alpha}{2}\right) \beta \ge 0,

    which, with :math:`\gamma > 0` and :math:`\alpha \le 2`, amounts to a non-negative skewness :math:`\beta`. Speeds
    are differences between consecutive samples: timestamps do not enter the computation and :math:`\gamma` is a ratio
    of quantile differences.

    Input: one position per call, the ``(dims,)`` point of a trajectory with ``dims`` equal to 2 or 3 (a ``(signals,
    dims)`` frame is rejected: average the markers before the call if one trajectory is wanted); ``process(frame, *,
    timestamp=None)``. The feature buffers ``window`` frames and computes every ``hop`` frames; ``timestamp`` is that of
    the newest frame.

    Parameters
    ----------
    window : int
        Frames per window, at least 6 (5 speeds are needed).
    hop : int, optional
        New frames between two windows, between 1 and ``window``. Defaults to ``1``.
    dims : int, optional
        Coordinates of the position, 2 or 3. Defaults to the size of the first position.
    method : {"constrained", "quantile"}, optional
        The fit. ``"constrained"`` (default) clamps :math:`\nu_\alpha` and :math:`\nu_\beta` to the range of the tables
        and always gives a result; ``"quantile"`` uses the unclamped values and linear percentiles, and fails when the
        window is outside the range of the tables. *(live)*

    Notes
    -----
    **Outputs.** ``is_sudden``: ``True`` when the window is classified as sudden. ``alpha``: stability parameter, in (0,
    2]. ``beta``: skewness parameter, in [-1, 1]. ``gamma``: scale parameter, not negative, computed from the quantile
    ratio.

    **Statuses.** ``WARMING_UP`` until the first window of ``window`` frames is full, ``NO_OUTPUT`` between two windows,
    ``INVALID_INPUT`` for NaN or infinite coordinates and, with ``method="quantile"``, when the distribution could not
    be fitted (no outputs). A window whose speeds are all equal, as for a trajectory at rest or at constant speed, gives
    the Gaussian fallback (:math:`\alpha = 2`, :math:`\beta = 0`, :math:`\gamma = 0`) and is classified as sudden.

    References
    ----------
    :cite:`mcculloch1986stable`, :cite:`mazzarino2009impulsivity`, :cite:`niewiadomski2015impulsive`

    Examples
    --------
    >>> import numpy as np
    >>> from pyeyesweb.mid_level import Suddenness
    >>> positions = np.cumsum(np.random.default_rng(0).normal(size=(40, 3)), axis=0)
    >>> record = Suddenness(window=20, hop=10).run(positions)
    >>> print(f"{record.alpha[19]:.2f} {record.beta[19]:.2f}", record.is_sudden[19])
    1.53 0.53 True
    """

    _OUTPUTS = Schema(
        Output("is_sudden", kind=bool, doc="Whether the movement is classified as sudden."),
        Output("alpha", doc="Stability parameter of the fitted stable distribution."),
        Output("beta", doc="Skewness parameter of the fitted stable distribution."),
        Output("gamma", unit="<length>/s", doc="Scale parameter of the fitted stable distribution."),
    )

    _core_class = core.motion.Suddenness
    _core_names = {"method": "algorithm"}
    _lazy_block = True

    def __init__(self, window: int, hop: int = 1, *, dims: Optional[int] = None, method: _Algorithm = "constrained"):
        super().__init__(window=window, hop=hop)
        self.dims = dims
        self.method = method
        self._check_window()

    def _process_window(self, series: Any, *, timestamp: Optional[float] = None) -> Result:
        pos = self._window_trajectory(series)
        if (unusable := self._unusable(pos, timestamp)) is not None:
            return unusable

        alpha, beta, gamma, is_sudden = self._block.process(pos)
        return self._fit_result(alpha, timestamp, is_sudden=is_sudden, alpha=alpha, beta=beta, gamma=gamma)


__all__ = ["Suddenness"]
