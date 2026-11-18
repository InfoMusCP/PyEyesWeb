"""Shape of contours: the salient points of a closed contour (body parts from curvature).

A contour is one frame of ``(x, y)`` points, an ``(N, 2)`` array; the first and the last point are neighbours (the
contour is closed). Every feature declares its outputs as a ``Schema`` (``feature.outputs``) and returns a ``Result``
(see ``pyeyesweb.data_models``).
"""

from typing import Any, Optional

import numpy as np

from pyeyesweb._core import core
from pyeyesweb.base.core_feature import XY, FrameFeature
from pyeyesweb.base.inputs import non_finite, points_input
from pyeyesweb.catalog import Layer, describe
from pyeyesweb.data_models.inputs import Inputs
from pyeyesweb.data_models.results import Output, Result, Schema, Status

_motion = core.motion

CONTOUR = points_input("contour", None, "contour points (x, y)", dims=2)


@describe(Layer.LOW_LEVEL, eyesweb="body_parts_from_curvature")
class BodyPartsFromCurvature(FrameFeature):
    r"""Contour points at the curvature extrema of a silhouette, tracked as labelled body parts.

    Finds the salient points of a closed contour, such as the head, hands and feet of a silhouette, as the extrema of
    its curvature, and gives them labels that stay with the same point from one call to the next. The feature takes the
    ``(x, y)`` points of the contour only: it estimates the curvature itself, at every point from the point and its two
    neighbours (the contour is closed, so the neighbours of the first point include the last one). With :math:`(x', y')`
    the step from the previous point to the point and :math:`(x'', y'')` the difference between the next step and this
    one, the curvature at the point is

    .. math::

        \kappa = \frac{x' y'' - y' x''}{\left(x'^2 + y'^2\right)^{3/2}},

    which is :math:`1 / R` for a circle of radius :math:`R` and 0 for a straight run of equally spaced points. It is
    positive where the contour turns counter-clockwise in the coordinate frame of the input and negative where it turns
    clockwise (in image coordinates, with y pointing down, the orientation on the screen is reversed); it is 0 where the
    point coincides with the next one.

    The contour is cut at the zero crossings of the curvature (at least ``minimum_distance`` points apart); in every
    piece, the extremum of larger magnitude is a minimum point when it is negative and a maximum point when it is
    positive. With ``track_points`` the labels of the previous call are carried over to the nearest new points (the
    feature keeps the previous points as its state), up to ``number_of_points`` of them; a maximum that moved farther
    than ``tracking_distance`` since the previous call loses its label.

    Input: ``process(contour, *, timestamp=None)``, the ``(N, 2)`` contour of one frame; ``run`` takes ``(T, N, 2)``.
    The curvature is a derivative of the points, so it amplifies their noise: smooth the contour before the feature.

    Parameters
    ----------
    minimum_distance : int, optional
        Minimum gap, in contour points, between two accepted zero crossings of the curvature. Defaults to ``5``.
        *(live)*
    number_of_points : int, optional
        Number of labels used when tracking: the maximum number of tracked maxima (``0`` tracks no maxima and keeps all
        the minima). It has no effect without tracking. Defaults to ``5``. *(live)*
    track_points : bool, optional
        Keep the labels of the extrema between calls. With ``False`` each call labels its points afresh. Defaults to
        ``True``. *(live)*
    tracking_distance : float, optional
        Largest move between two calls, in the unit of the contour, of a maximum that keeps its label; > 0. Defaults to
        ``0.05``, the constant of the original block, which suits a normalised contour: for a contour in pixels pass a
        few pixels. *(live)*

    Notes
    -----
    **Outputs.** ``minimums`` and ``maximums``: the contour points at the curvature extrema, ``(x, y)`` each, in the
    unit of the contour. They are labelled outputs, ``label -> (x, y)`` with labels ``label_min<i>`` and
    ``label_max<i>``; their number depends on the contour.

    **Statuses.** ``INVALID_INPUT`` for an empty contour or NaN or infinite coordinates; otherwise ``OK``.

    Changed (design review 2026-11-17): the feature took the curvature of each point as a first input, computed by the
    public ``ContourCurvature`` feature. That feature had no use on its own and is gone: the curvature is computed here.
    Corrected in the core: the curvature values are aligned with the contour points (value ``i`` at point ``i``; the
    sequence used to be rotated by one point), and when the last piece of the contour wraps around into the first, the
    merged extremum keeps the point of that extremum together with its value.

    Examples
    --------
    >>> import numpy as np
    >>> from pyeyesweb.low_level import BodyPartsFromCurvature
    >>> t = np.linspace(0.0, 2.0 * np.pi, 200, endpoint=False)
    >>> r = 10.0 + 3.0 * np.cos(5.0 * t)
    >>> contour = np.column_stack([r * np.cos(t), r * np.sin(t)])
    >>> parts = BodyPartsFromCurvature().process(contour)
    >>> print(len(parts.minimums), len(parts.maximums))
    5 5
    """
    _core_class = _motion.BodyPartsFromCurvature
    _INPUTS = Inputs(CONTOUR)

    def __init__(self, **params: Any):
        self._curvature_block = _motion.ContourCurvature()  # the curvature of each contour point; it keeps no state
        super().__init__(**params)

    def _schema(self) -> Schema:
        return Schema(Output("minimums", components=XY, labelled=True, unit="<length>", doc="points at curvature minima"),
                      Output("maximums", components=XY, labelled=True, unit="<length>", doc="points at curvature maxima"))

    def _process(self, contour: Any, timestamp: Optional[float]) -> Result:
        if reason := non_finite(contour):
            return self._no_output(Status.INVALID_INPUT, reason, timestamp)
        contour = np.asarray(contour, dtype=float)
        return self._to_result(self._block.process(self._curvature_block.process(contour), contour), timestamp)

    def _to_result(self, raw: Any, timestamp: Optional[float]) -> Result:
        minimums, maximums = raw
        return self._result(timestamp=timestamp, minimums=minimums, maximums=maximums)


__all__ = ["BodyPartsFromCurvature"]
