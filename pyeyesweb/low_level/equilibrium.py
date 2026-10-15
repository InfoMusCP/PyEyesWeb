"""Equilibrium of a posture: where the barycenter lies within the support region of the two feet.

The feature takes the two feet and the barycenter as points on the floor plane and measures how well the barycenter is
centred inside an elliptical support region built around the feet.
"""

from typing import Any, Optional

import numpy as np

from pyeyesweb.catalog import Layer, describe
from pyeyesweb.base.inputs import non_finite
from pyeyesweb.data_models.inputs import Input, InputKind, Inputs
from pyeyesweb.data_models.results import Output, Result, Schema, Status
from pyeyesweb._core import core
from pyeyesweb.base.core_feature import CoreFeature


@describe(Layer.LOW_LEVEL)
class Equilibrium(CoreFeature):
    r"""Equilibrium of a barycenter within the elliptical support region between two feet.

    Estimates the postural balance of a person from one snapshot of the floor plane: the barycenter is well balanced
    when it lies near the centre of the segment joining the feet, and the balance is lost when it leaves the support
    region. The support region is an ellipse centred midway between the left foot :math:`P_L` and the right foot
    :math:`P_R`, with its major axis along the line through the feet. With :math:`d = \lVert P_R - P_L \rVert` and the
    margin :math:`m`, its semi-axes are

    .. math::

        a = \frac{d}{2} + m, \qquad b = m \, w_y,

    where :math:`w_y` is ``y_weight``. Let :math:`(x', y')` be the position of the barycenter relative to the centre of
    the ellipse, rotated so that the first axis runs from the left foot to the right foot. Then

    .. math::

        q = \left(\frac{x'}{a}\right)^2 + \left(\frac{y'}{b}\right)^2, \qquad
        E = \begin{cases} 1 - \sqrt{q} & q \le 1 \\ 0 & q > 1 \end{cases}

    so that :math:`E` is 1 when the barycenter is exactly at the centre of the support and falls linearly with the
    normalised distance to 0 on the boundary of the ellipse and outside it. The ``angle`` output is the direction of the
    foot-to-foot vector, :math:`\operatorname{atan2}(y_R - y_L, x_R - x_L)`, in degrees.

    Three inputs, each an ``(x, y)`` point on the floor plane: ``process(left_foot, right_foot, barycenter, *,
    timestamp=None)``; ``run`` takes the three recordings in the same order. The barycenter is computed by the caller,
    and so is the projection onto the floor: for Y-up data (for example Qualisys) take the columns ``[0, 2]``, as in
    ``positions.mean(axis=0)[[0, 2]]``. The feature keeps no state.

    Parameters
    ----------
    margin : float, optional
        Safety margin added to the support ellipse, in metres (it is written in metres whatever the unit of the data,
        and multiplied by 1000 when ``units="mm"``). It also sets the semi-minor axis of the ellipse together with
        ``y_weight``. Defaults to ``0.1`` m. *(live)*
    y_weight : float, optional
        Dimensionless weight of the margin in the semi-minor axis of the ellipse, :math:`b = m \, w_y`. Defaults to
        ``0.5``. *(live)*
    units : {"m", "mm"}, optional
        Unit of the data (the feet and barycenter coordinates); the data and the outputs are never scaled, only
        ``margin`` is. Defaults to ``"m"``.

    Notes
    -----
    **Outputs.** ``equilibrium``: dimensionless, in [0, 1], 1 when the barycenter is at the centre of the support.
    ``angle``: degrees, in [-180, 180], direction of the vector from the left to the right foot.

    **Statuses.** ``INVALID_INPUT`` for an empty or non-finite point and when the two feet coincide (there is no support
    vector); every output is then empty.

    The default margin is 0.1 m; it was 100 mm in the original block, whose lengths were in millimetres, and the same
    numbers are obtained for the same coordinates by passing ``units="mm"``.

    References
    ----------
    :cite:`ghisio2015exergames`

    Examples
    --------
    >>> from pyeyesweb.low_level import Equilibrium
    >>> equilibrium = Equilibrium(margin=0.1)
    >>> centred = equilibrium.process((-0.1, 0.0), (0.1, 0.0), (0.0, 0.0))
    >>> print(f"{centred.equilibrium:.2f} {centred.angle:.0f}")
    1.00 0
    >>> print(f"{equilibrium.process((-0.1, 0.0), (0.1, 0.0), (0.1, 0.0)).equilibrium:.2f}")
    0.50
    """

    _OUTPUTS = Schema(
        Output("equilibrium", doc="Equilibrium in [0, 1]: 1 is perfectly centred, 0 is outside the support ellipse."),
        Output("angle", unit="deg", doc="Angle of the foot-to-foot support vector."),
    )
    _INPUTS = Inputs(*(Input(name, InputKind.SAMPLE, (2,), doc=f"{name} (x, y) on the floor plane")
                      for name in ("left_foot", "right_foot", "barycenter")))
    _core_class = core.motion.Equilibrium
    _lazy_block = True
    _unit_params = {"margin": 1}  # a length: written in metres, scaled for `units="mm"` data

    def __init__(
            self,
            *,
            margin: float = 0.1,
            y_weight: float = 0.5,
            units: str = "m"
    ):
        super().__init__(units=units)
        self.margin = margin
        self.y_weight = y_weight

    @property
    def margin(self) -> float:
        """Safety margin added to the support ellipse (metres; scaled for ``units="mm"``)."""
        return self._params["margin"]

    @margin.setter
    def margin(self, value: float):
        self._set_param("margin", float(value))

    @property
    def y_weight(self) -> float:
        """Weighting factor for the semi-minor axis."""
        return self._params["y_weight"]

    @y_weight.setter
    def y_weight(self, value: float):
        self._set_param("y_weight", float(value))

    def process(self, left_foot: Any, right_foot: Any, barycenter: Any, *, timestamp: Optional[float] = None) -> Result:
        """Elliptical equilibrium of one posture: outputs ``equilibrium`` (in [0, 1]) and ``angle`` (degrees).

        ``INVALID_INPUT`` for an empty or non-finite point, and when the feet coincide (no support vector).
        """
        points = [np.asarray(point, dtype=float) for point in (left_foot, right_foot, barycenter)]
        for point in points:
            if reason := non_finite(point):
                return self._no_output(Status.INVALID_INPUT, reason, timestamp)
        result = self._block.process(*(tuple(point.tolist()) for point in points))
        coincide = bool((points[0] == points[1]).all())
        return self._result(status=Status.INVALID_INPUT if coincide else Status.OK,
                           reason="the feet coincide: no support vector" if coincide else "",
                           equilibrium=result.value, angle=result.angle, timestamp=timestamp)


__all__ = ['Equilibrium']
