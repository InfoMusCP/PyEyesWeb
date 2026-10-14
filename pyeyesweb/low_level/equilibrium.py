"""Barycenter and equilibrium analysis for postural snapshots.

This module provides features for analysing postural balance. It computes the
relationship between two support points (e.g. feet) and a barycenter to
estimate the stability of a movement.
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
    """Elliptical equilibrium evaluation between two feet and a barycenter (maths in the compiled core).

    Computes how well the barycenter is centered between two support points
    using an elliptical model.

    !!! note
        This method relies on 2D projections of the 3D joints: the caller picks the floor plane.

    Read more in the [User Guide](../../user_guide/theoretical_framework/low_level/postural_balance.md).

    Three inputs, `(x, y)` points on the floor plane: `process(left_foot, right_foot, barycenter, timestamp=None)` and
    `run(left_foot, right_foot, barycenter, timestamps=None)`; stateless. The barycenter is computed by the caller, and
    so is the projection onto the floor: for Y-up data (Qualisys) take the columns `[0, 2]`, e.g.
    `barycenter = positions.mean(axis=0)[[0, 2]]`. `timestamp` is the timestamp in seconds (`NaN` when not given).

    Parameters
    ----------
    margin : float, optional
        Safety margin added to the support ellipse, in the unit of the points. It is written in metres, like the
        other lengths of the library, and multiplied by 1000 when `units="mm"`. Defaults to `0.1` (the 100 mm of
        the original, whose margin was in millimetres).
    y_weight : float, optional
        Weighting factor for the semi-minor axis of the ellipse (`margin * y_weight`).
        Defaults to `0.5`.
    units : {"m", "mm"}, optional
        Unit of the data; `margin` is scaled by 1000 for `"mm"`. Defaults to `"m"`.

    Examples
    --------
    >>> eq = Equilibrium(margin=0.1, y_weight=0.5)
    >>> result = eq.process(left_foot=(-0.1, 0.0), right_foot=(0.1, 0.0), barycenter=(0.0, 0.0))
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
        """Safety margin added to the support ellipse (metres; scaled for `units="mm"`)."""
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
        """Elliptical equilibrium of one posture: outputs `equilibrium` (in `[0, 1]`) and `angle` (degrees).

        `Status.INVALID_INPUT` for an empty or non-finite point, and when the feet coincide (no support vector).
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
