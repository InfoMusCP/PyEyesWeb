"""Shape of contours: contour filter, curvature, convex hull and body parts from curvature.

A contour is one frame of ``(x, y)`` points, an ``(N, 2)`` array; the first and the last point are neighbours (the
contour is closed). Every feature declares its outputs as a ``Schema`` (``feature.outputs``) and returns a ``Result``
(see ``pyeyesweb.data_models``).
"""

from typing import Any, Optional

import numpy as np

from pyeyesweb._core import core
from pyeyesweb.base.core_feature import XY, CoreFeature, FrameFeature
from pyeyesweb.base.inputs import non_finite, points_input
from pyeyesweb.catalog import Layer, describe
from pyeyesweb.data_models.inputs import Input, InputKind, Inputs
from pyeyesweb.data_models.results import Output, Result, Schema, Status

_motion = core.motion

CONTOUR = points_input("contour", None, "contour points (x, y)", dims=2)


class ContourFeature(FrameFeature):
    """A feature taking one ``(N, 2)`` contour per call; an empty or non-finite one is ``INVALID_INPUT``."""
    _INPUTS = Inputs(CONTOUR)

    def _process(self, contour: Any, timestamp: Optional[float]) -> Result:
        if reason := non_finite(contour):
            return self._no_output(Status.INVALID_INPUT, reason, timestamp)
        return self._to_result(self._block.process(contour), timestamp)


@describe(Layer.LOW_LEVEL, eyesweb="filter_contour (FilterContour)")
class FilterContour(ContourFeature):
    r"""Circular Gaussian smoothing of a closed 2D contour.

    Smooths the coordinates of a closed contour, for instance the outline of a silhouette, by convolving each coordinate
    with a Gaussian kernel. The kernel has ``window`` samples centred on the sample being filtered, with weights
    proportional to :math:`\exp\!\big(-(i - \lfloor w / 2 \rfloor)^2 / (2 \sigma^2)\big)` for :math:`i = 0, \dots, w -
    1` and normalised to sum 1, where :math:`w` is ``window`` and :math:`\sigma` is ``gaussian_sigma``. The contour is
    treated as closed: the neighbours of the first point include the last ones, and the other way round.

    Input: one contour per call, an ``(N, 2)`` array; ``process(frame, *, timestamp=None)`` (``run`` takes ``(T, N,
    2)``). The feature keeps no state.

    Parameters
    ----------
    window : int, optional
        Number of samples of the Gaussian kernel, at least 1. It must be shorter than the contour, otherwise the call
        has no output. Defaults to ``3``. *(live)*
    gaussian_sigma : float, optional
        Standard deviation of the Gaussian, in samples (not in length units), not negative; ``0`` gives NaN coordinates.
        Defaults to ``3.0``. *(live)*

    Notes
    -----
    **Outputs.** ``contour``: ``(N, 2)`` smoothed contour (components x and y), in the unit of the input.

    **Statuses.** ``NO_OUTPUT`` when ``window`` is not shorter than the contour; ``INVALID_INPUT`` for an empty contour
    or NaN or infinite coordinates.

    Examples
    --------
    >>> import numpy as np
    >>> from pyeyesweb.low_level import FilterContour
    >>> theta = np.linspace(0.0, 2.0 * np.pi, 60, endpoint=False)
    >>> circle = np.column_stack([np.cos(theta), np.sin(theta)])
    >>> smooth = FilterContour(window=5, gaussian_sigma=1.0).process(circle)
    >>> print(smooth.contour.shape, f"{np.hypot(*smooth.contour[0]):.3f}")
    (60, 2) 0.995
    """
    _core_class = _motion.FilterContour
    _core_names = {"window": "window_length", "gaussian_sigma": "sigma_value"}

    def _schema(self) -> Schema:
        return Schema(Output("contour", (None, 2), components=XY, unit="<length>", doc="smoothed contour"))

    def _to_result(self, raw: np.ndarray, timestamp: float) -> Result:
        if len(raw) == 0:
            return self._no_output(Status.NO_OUTPUT, "contour not longer than the filter window", timestamp)
        return self._result(timestamp=timestamp, contour=raw)


@describe(Layer.LOW_LEVEL, eyesweb="contourstolist (CurvatureFunction)")
class ContourCurvature(ContourFeature):
    r"""Signed curvature at every point of a closed 2D contour.

    Estimates the curvature of a closed contour, for instance the outline of a silhouette, from each point and its two
    neighbours (the contour is closed, so the neighbours of the first point include the last one). With :math:`(x', y')`
    the step from the previous point to the point and :math:`(x'', y'')` the difference between the next step and this
    one, the curvature at the point is

    .. math::

        \kappa = \frac{x' y'' - y' x''}{\left(x'^2 + y'^2\right)^{3/2}},

    which is :math:`1 / R` for a circle of radius :math:`R` and 0 for a straight run of equally spaced points. It is
    positive where the contour turns counter-clockwise in the coordinate frame of the input and negative where it turns
    clockwise (in image coordinates, with y pointing down, the orientation on the screen is reversed); it is 0 where the
    point coincides with the next one. The values feed ``BodyPartsFromCurvature``.

    Input: one contour per call, an ``(N, 2)`` array; ``process(frame, *, timestamp=None)`` (``run`` takes ``(T, N,
    2)``). The feature has no parameters and keeps no state.

    Notes
    -----
    **Outputs.** ``curvature``: ``(N,)``, one value per contour point (value ``i`` belongs to point ``i``), in the
    inverse of the unit of the input.

    **Statuses.** ``INVALID_INPUT`` for an empty contour or NaN or infinite coordinates; otherwise ``OK``.

    Corrected in the core: the curvature values are aligned with the contour points (value ``i`` at point ``i``); the
    sequence used to be rotated by one point.

    Examples
    --------
    >>> import numpy as np
    >>> from pyeyesweb.low_level import ContourCurvature
    >>> theta = np.linspace(0.0, 2.0 * np.pi, 60, endpoint=False)
    >>> circle = np.column_stack([2.0 * np.cos(theta), 2.0 * np.sin(theta)])
    >>> print(np.round(ContourCurvature().process(circle).curvature[:3], 2))
    [0.5 0.5 0.5]
    """
    _core_class = _motion.ContourCurvature

    def _schema(self) -> Schema:
        return Schema(Output("curvature", (None,), unit="1/<length>", doc="curvature per contour point"))

    def _to_result(self, raw: np.ndarray, timestamp: float) -> Result:
        return self._result(timestamp=timestamp, curvature=raw)


@describe(Layer.LOW_LEVEL, eyesweb="body_parts_from_curvature")
class BodyPartsFromCurvature(CoreFeature):
    """Contour points at the curvature extrema of a silhouette, tracked as labelled body parts.

    Finds the salient points of a closed contour, such as the head, hands and feet of a silhouette, as the extrema of
    its curvature, and gives them labels that stay with the same point from one call to the next. The contour is cut at
    the zero crossings of the curvature (at least ``minimum_distance`` points apart); in every piece, the extremum of
    larger magnitude is a minimum point when it is negative and a maximum point when it is positive. With
    ``track_points`` the labels of the previous call are carried over to the nearest new points (the feature keeps the
    previous points as its state), up to ``number_of_points`` of them.

    Input: ``process(curvature, contour, *, timestamp=None)``, the ``(N,)`` curvature of each point of the ``(N, 2)``
    contour (for example from ``ContourCurvature``); ``run`` takes ``(T, N)`` and ``(T, N, 2)`` recordings.

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

    Notes
    -----
    **Outputs.** ``minimums`` and ``maximums``: the contour points at the curvature extrema, ``(x, y)`` each, in the
    unit of the contour. They are labelled outputs, ``label -> (x, y)`` with labels ``label_min<i>`` and
    ``label_max<i>``; their number depends on the contour.

    **Statuses.** ``OK`` always; ``ValueError`` when the curvature and the contour have a different number of points.

    Corrected in the core: when the last piece of the contour wraps around into the first, the merged extremum keeps the
    point of that extremum together with its value (it used to keep the point index of another extremum).

    Examples
    --------
    >>> import numpy as np
    >>> from pyeyesweb.low_level import BodyPartsFromCurvature, ContourCurvature
    >>> t = np.linspace(0.0, 2.0 * np.pi, 200, endpoint=False)
    >>> r = 10.0 + 3.0 * np.cos(5.0 * t)
    >>> contour = np.column_stack([r * np.cos(t), r * np.sin(t)])
    >>> parts = BodyPartsFromCurvature().process(ContourCurvature().process(contour).curvature, contour)
    >>> print(len(parts.minimums), len(parts.maximums))
    5 5
    """
    _core_class = _motion.BodyPartsFromCurvature
    _core_names = {"number_of_points": "points_number"}
    _INPUTS = Inputs(Input("curvature", InputKind.SAMPLE, (None,), doc="curvature of each contour point"), CONTOUR)

    def _schema(self) -> Schema:
        return Schema(Output("minimums", components=XY, labelled=True, unit="<length>", doc="points at curvature minima"),
                      Output("maximums", components=XY, labelled=True, unit="<length>", doc="points at curvature maxima"))

    def process(self, curvature: Any, contour: Any, *, timestamp: Optional[float] = None) -> Result:
        if len(np.atleast_1d(curvature)) != len(contour) and len(contour) and np.size(curvature):
            raise ValueError(f"BodyPartsFromCurvature: curvature holds {len(np.atleast_1d(curvature))} values but "
                             f"contour {len(contour)} points: one curvature per contour point")
        return self._to_result(self._block.process(curvature, contour), timestamp)

    def _to_result(self, raw: Any, timestamp: Optional[float]) -> Result:
        minimums, maximums = raw
        return self._result(timestamp=timestamp, minimums=minimums, maximums=maximums)


@describe(Layer.LOW_LEVEL, eyesweb="ConvexHull")
class ConvexHull(ContourFeature):
    """Convex hull polygon of a 2D contour.

    Gives the smallest convex polygon that contains all the points of a contour, for instance the outline of a
    silhouette, as the list of its vertices. Only strictly convex vertices are kept (collinear points on an edge are
    dropped). The vertices run clockwise when y points up (counter-clockwise on a screen in image coordinates), starting
    from the point with the smallest x, and from the smallest y among those. The hull is that of the exact input
    coordinates.

    Input: one contour per call, an ``(N, 2)`` array; ``process(frame, *, timestamp=None)`` (``run`` takes ``(T, N,
    2)``). The feature keeps no state.

    Parameters
    ----------
    integer_coordinates : bool, optional
        Require integer coordinates, as the pixel contours of an image have. When ``True``, a contour with fractional
        coordinates raises ``ValueError``; when ``False`` any real coordinates are accepted. It only validates the
        input: the hull is the same in both cases (the core's own default is ``True``, the EyesWeb integer contour
        datatype). Defaults to ``False``. *(live)*

    Notes
    -----
    **Outputs.** ``hull``: ``(H, 2)`` vertices of the hull (components x and y), in the unit of the input.

    **Statuses.** ``INVALID_INPUT`` for an empty contour or NaN or infinite coordinates.

    Corrected in the core: the hull of a contour with real coordinates is computed on the exact input points; the
    coordinates used to be quantised to multiples of 0.001. The orientation tests are exact for any range of
    coordinates.

    Examples
    --------
    >>> import numpy as np
    >>> from pyeyesweb.low_level import ConvexHull
    >>> contour = np.array([[0, 0], [4, 0], [4, 4], [0, 4], [2, 2]])
    >>> print(ConvexHull().process(contour).hull)
    [[0. 0.]
     [0. 4.]
     [4. 4.]
     [4. 0.]]
    """
    _core_class = _motion.ConvexHull

    def __init__(self, integer_coordinates: bool = False):
        super().__init__(integer_coordinates=integer_coordinates)

    def _schema(self) -> Schema:
        return Schema(Output("hull", (None, 2), components=XY, unit="<length>", doc="convex hull vertices"))

    def _to_result(self, raw: np.ndarray, timestamp: float) -> Result:
        return self._result(timestamp=timestamp, hull=raw)


__all__ = ["FilterContour", "ContourCurvature", "ConvexHull", "BodyPartsFromCurvature"]
