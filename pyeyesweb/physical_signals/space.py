"""Detection of the grid cell hit by a point (EyesWeb HitCellDetector).

A 2D area is divided into a grid of ``cells_along_y`` rows (from the y coordinate) and ``cells_along_x`` columns (from the
x coordinate); a cell is ``(i, j)`` = (row, column). The feature declares its outputs as a
:class:`~pyeyesweb.data_models.Schema` (``feature.outputs``) and returns a :class:`~pyeyesweb.data_models.Result`. The
potentials driven by the hit cells are in :mod:`pyeyesweb.mid_level.space_occupation`.
"""

from typing import Any, Optional

import numpy as np

from pyeyesweb._core import core
from pyeyesweb.base.inputs import points_input
from pyeyesweb.catalog import Layer, describe
from pyeyesweb.data_models.inputs import Inputs
from pyeyesweb.data_models.results import Output, Result, Schema, Status
from pyeyesweb.base.core_feature import FrameFeature


@describe(Layer.PHYSICAL_SIGNALS, eyesweb="HitCellDetector")
class HitCellDetector(FrameFeature):
    r"""The grid cells hit by a list of 2D points.

    A rectangular area of the plane, :math:`[x_{min}, x_{max}] \times [y_{min}, y_{max}]`, is divided into a grid of
    ``cells_along_y`` rows (along the y coordinate) and ``cells_along_x`` columns (along the x coordinate). Each point is
    located in the grid: a cell is the pair ``(i, j)`` = (row, column),

    .. math::

        i = \left\lfloor \frac{y - y_{min}}{y_{max} - y_{min}}\, n_y \right\rfloor, \qquad
        j = \left\lfloor \frac{x - x_{min}}{x_{max} - x_{min}}\, n_x \right\rfloor,

    with the upper edge of the area belonging to the last cell. It is the first step of the space-occupation features, which
    turn the hit cells into potentials (:mod:`pyeyesweb.mid_level.space_occupation`).

    ``process(points, *, timestamp=None)`` takes an ``(N, 2)`` array of ``(x, y)`` (``run`` takes ``(T, N, 2)``); the
    feature is stateless and has no time axis: ``timestamp`` is only copied into ``result.timestamp``.

    Parameters
    ----------
    cells_along_x : int, default 10
        Number of columns of the grid (``n_x``), >= 1 *(live)*.
    cells_along_y : int, default 10
        Number of rows of the grid (``n_y``), >= 1 *(live)*.
    x_min, x_max : float, default 0.0 and 1.0
        Extent of the monitored area along x, in metres *(live)*; ``units`` says in what unit your points are given and
        the parameter is converted, never the data.
    y_min, y_max : float, default 0.0 and 1.0
        Extent of the monitored area along y, in metres *(live)*, as for x.
    clip_values : bool, default True
        A point outside the area is moved to the nearest cell *(live)*. Off, such a point makes the call
        ``INVALID_INPUT``.
    units : {"m", "mm"}, default "m"
        Unit of your points *(live)*; the area parameters are always written in metres.

    Notes
    -----
    **Outputs.** ``cells``: ``(n, 2)`` integer array of ``(i, j)`` (row from y, column from x), dimensionless indices
    counted from 0 in the order of the input points; an empty input gives an empty array, as EyesWeb outputs an empty list.
    The result is ``OK`` for every valid call. With ``clip_values=False`` a point outside the area makes the call
    ``INVALID_INPUT`` with the reason ``"point out of range (clip_values is off)"``.

    Examples
    --------
    >>> from pyeyesweb.physical_signals import HitCellDetector
    >>> detector = HitCellDetector(cells_along_x=4, cells_along_y=2)
    >>> detector.process([[0.1, 0.1], [0.9, 0.6], [1.5, -1.0]]).cells.tolist()    # the last point is clipped
    [[0, 0], [1, 3], [0, 3]]
    """
    _core_class = core.space.HitCellDetector
    _core_names = {"cells_along_x": "cells_x", "cells_along_y": "cells_y"}
    _unit_params = {"x_min": 1, "x_max": 1, "y_min": 1, "y_max": 1}  # lengths of the monitored area
    _INPUTS = Inputs(points_input("points", None, "2D points to locate in the grid", dims=2))

    def _schema(self) -> Schema:
        return Schema(Output("cells", (None, 2), kind=int, components=("i", "j"), unit="cells",
                             doc="hit cell (row from y, column from x) of each point"))

    def _process(self, points: Any, timestamp: Optional[float]) -> Result:
        return self._to_result(self._block.process(points), timestamp)

    def _to_result(self, raw: Optional[np.ndarray], timestamp: float) -> Result:
        if raw is None:
            return self._no_output(Status.INVALID_INPUT, "point out of range (clip_values is off)", timestamp)
        return self._result(timestamp=timestamp, cells=raw)


__all__ = ["HitCellDetector"]
