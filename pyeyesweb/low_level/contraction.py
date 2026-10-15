"""Contraction and expansion of a body configuration in 3D: bounding-box filled area, ellipsoid sphericity and points
density.

Each feature takes one frame of points and measures how compact or spread out the configuration is, independently of
where the body is and, for the first two, of the unit of the data.
"""

from typing import Any, Optional, Sequence, Tuple

import numpy as np

from pyeyesweb._core import core
from pyeyesweb.base.core_feature import XYZ, FrameFeature
from pyeyesweb.catalog import Layer, describe
from pyeyesweb.data_models.inputs import Inputs
from pyeyesweb.data_models.results import Output, Result, Schema, Status
from pyeyesweb.base.inputs import labelled_set, non_finite, points_input
from pyeyesweb.skeletons import with_skeleton


_MIN_RADIUS = 1e-6  # the C++ threshold below which the major radius is zero


@describe(Layer.LOW_LEVEL)
class BoundingBoxFilledArea(FrameFeature):
    r"""Contraction index of a 3D posture: convex hull area over bounding box area.

    Measures how much of the axis-aligned box that encloses a posture is filled by the convex hull of its points, a
    proxy for how contracted or expanded the body is. The index is the ratio of the surface area of the convex hull to
    the surface area of the bounding box:

    .. math::

        I = \frac{A_{\mathrm{hull}}}{A_{\mathrm{box}}}, \qquad
        A_{\mathrm{box}} = 2\,(\Delta_x \Delta_y + \Delta_x \Delta_z + \Delta_y \Delta_z),

    where :math:`\Delta_x, \Delta_y, \Delta_z` are the extents of the points along the three axes. The hull lies inside
    the box, so :math:`0 \le I \le 1`: the eight corners of a box give 1, the six vertices of an octahedron inscribed in
    a cube give :math:`\sqrt{3}/6 \approx 0.289`. The index is dimensionless and independent of the unit of the data.

    The feature has no parameters and keeps no state. ``process(frame, *, timestamp=None)`` takes one frame, an ``(N,
    3)`` array of points (any other width raises ``ValueError``); ``timestamp`` (seconds) is only reported on the
    result.

    Notes
    -----
    **Outputs.** ``contraction_index``: dimensionless, in [0, 1].

    **Statuses.** ``INVALID_INPUT`` (the index is empty) for a frame with no points, with NaN or infinite coordinates,
    with fewer than 4 points, with coplanar or collinear points (the 3D hull is degenerate), or whose bounding box has
    an area of at most 1e-6 (in the squared unit of the data). Such a frame used to give an index of 0 with status
    ``OK``.

    References
    ----------
    :cite:`camurri2003recognizing`, :cite:`glowinski2011minimal`

    Examples
    --------
    >>> import numpy as np
    >>> from pyeyesweb.low_level import BoundingBoxFilledArea
    >>> corners = np.array([[x, y, z] for x in (0, 1) for y in (0, 1) for z in (0, 1)], dtype=float)
    >>> result = BoundingBoxFilledArea().process(corners)
    >>> print(f"{result.contraction_index:.3f}")
    1.000
    """

    _OUTPUTS = Schema(Output("contraction_index", doc="Ratio of convex hull area to bounding box area."))
    _INPUTS = Inputs(points_input("points", None, "points of the body configuration"))

    EPSILON = 1e-6

    _core_class = core.motion.BoundingBoxFilledArea

    def __init__(self):
        super().__init__(epsilon=self.EPSILON)

    def _process(self, points: Any, timestamp: Optional[float]) -> Result:
        points = np.ascontiguousarray(points, dtype=np.float64)
        if reason := non_finite(points):
            return self._no_output(Status.INVALID_INPUT, reason, timestamp)
        extent = np.ptp(points, axis=0)  # the block's own test: a box of area <= epsilon gives index 0
        degenerate = 2 * (extent[0] * extent[1] + extent[0] * extent[2] + extent[1] * extent[2]) <= self._param("epsilon", self.EPSILON)
        reason = ""
        if degenerate:
            reason = "the bounding box has no extent"
        elif len(points) < 4:
            reason = "fewer than 4 points: the 3D convex hull is degenerate"
        elif np.linalg.matrix_rank(points - points.mean(axis=0)) < 3:
            reason = "the points are coplanar or collinear: the 3D convex hull is degenerate"
        return self._to_result(self._block.process(points), timestamp, reason)

    def _to_result(self, raw: float, timestamp: Optional[float], reason: str = "") -> Result:
        return self._result(status=Status.INVALID_INPUT if reason else Status.OK, reason=reason,
                           contraction_index=raw, timestamp=timestamp)


@describe(Layer.LOW_LEVEL, eyesweb="PointsDensity3D")
class PointsDensity(FrameFeature):
    r"""Dispersion of a set of 3D points around their centroid.

    Measures how widely a configuration of points, for instance the joints of a skeleton, is spread around its centre:
    small when the points are clustered (contracted posture), large when they are far apart (expanded posture). With
    :math:`c` the centroid of the points :math:`x_i` (their mean, or the per-axis median) and :math:`d_i = \lVert x_i -
    c \rVert` their Euclidean distances to it, the density is an aggregate of the distances:

    .. math::

        D = \operatorname{agg}_i \, d_i, \qquad
        \operatorname{agg} \in \{\text{mean}, \text{median}, \max, \textstyle\sum\}.

    With ``output_dims="components"`` the aggregate is taken per axis over the absolute deviations :math:`\lvert x_{i,k}
    - c_k \rvert` and ``density`` is a vector of three values.

    Input: one set of points per call, an ``(N, 3)`` array or a dictionary ``label -> (x, y, z)``; ``process(frame, *,
    timestamp=None)``. The labels name the rows of an array and do not enter the computation.

    Parameters
    ----------
    labels : sequence of str, optional
        Names of the points of array input, in row order. Given by ``skeleton`` when that is passed. *(structural)*
    skeleton : str or Skeleton, optional
        A device preset or a user-defined ``Skeleton`` that provides ``labels``.
    centroid_type : {"mean", "median"}, optional
        The centroid: the mean of the points or their per-axis median. Defaults to ``"mean"``. *(live)*
    distance_type : {"mean", "median", "max", "sum_of_lengths"}, optional
        How the distances to the centroid are aggregated. Defaults to ``"mean"``. *(live)*
    output_dims : {"module", "components"}, optional
        ``"module"``: ``density`` is a scalar built from the Euclidean distances. ``"components"``: ``density`` has
        three components (x, y, z) built from the per-axis deviations. Defaults to ``"module"``. *(live)*

    Notes
    -----
    **Outputs.** ``density``: scalar, or ``(3,)`` for ``"components"``, in the unit of the data, not negative.
    ``centroid``: ``(3,)``, the centroid, in the unit of the data.

    **Statuses.** ``INVALID_INPUT`` for a set with no points or with NaN or infinite coordinates. The median is the
    exact median of the values.

    References
    ----------
    :cite:`camurri2003recognizing`, :cite:`glowinski2011minimal`

    Examples
    --------
    >>> import numpy as np
    >>> from pyeyesweb.low_level import PointsDensity
    >>> points = np.array([[0.0, 0, 0], [2, 0, 0], [0, 2, 0], [0, 0, 2]])
    >>> result = PointsDensity().process(points)
    >>> print(f"{result.density:.3f}", result.centroid)
    1.460 [0.5 0.5 0.5]
    """
    _core_class = core.motion.PointsDensity

    def __init__(self, labels: Optional[Sequence[str]] = None, skeleton: Any = None, **params: Any):
        labels, params = with_skeleton(skeleton, labels, params)
        super().__init__(**params)
        self._labels = None if labels is None else tuple(labels)

    @property
    def labels(self) -> Optional[Tuple[str, ...]]:
        """The names of the points of array input (``None``: by index)."""
        return self._labels

    def _inputs(self) -> Inputs:
        return Inputs(points_input("points", self._labels, "points whose dispersion is measured", accepts=(dict,)))

    def _schema(self) -> Schema:
        dim = self._param("output_dims", core.motion.PointsDensityDistanceDim.MODULE)
        if dim == core.motion.PointsDensityDistanceDim.MODULE:
            density = Output("density", unit="<length>", doc="dispersion around the centroid")
        else:
            density = Output("density", components=XYZ, unit="<length>", doc="per-axis dispersion around the centroid")
        return Schema(density, Output("centroid", components=XYZ, unit="<length>"))

    def _process(self, points: Any, timestamp: Optional[float]) -> Result:
        raw = self._block.process(labelled_set(points, self._labels, "PointsDensity", anonymous=True))
        if raw is None:
            return self._no_output(Status.INVALID_INPUT, "no points", timestamp)
        return self._to_result(raw, timestamp)

    def _to_result(self, raw: Any, timestamp: Optional[float]) -> Result:
        density, centroid = np.asarray(raw[0], dtype=float), np.asarray(raw[1], dtype=float)
        finite = np.isfinite(density).all() and np.isfinite(centroid).all()
        return self._result(status=Status.OK if finite else Status.INVALID_INPUT,
                           reason="" if finite else "NaN or infinite coordinates",
                           density=density if density.ndim else float(density), centroid=centroid, timestamp=timestamp)


@describe(Layer.LOW_LEVEL, eyesweb="EllipsoidSphericity (EllipsoidSphericity3D)")
class EllipsoidSphericity(FrameFeature):
    r"""Sphericity of the ellipsoid fitted to a point cloud, or of one given by its three axes.

    Quantifies how close a posture is to a sphere rather than to an elongated or flat shape. The point cloud is
    summarised by the ellipsoid whose radii :math:`a \ge b \ge c` are the square roots of the eigenvalues of the sample
    covariance matrix of the points (principal component analysis, so the result does not depend on the orientation of
    the body). Two indices are derived from the radii: the axis ratio :math:`c / a`, and the Wadell sphericity, the
    ratio between the surface area of the sphere with the volume of the ellipsoid and the surface area of the ellipsoid:

    .. math::

        \Psi = \frac{\pi^{1/3} (6 V)^{2/3}}{A}, \qquad V = \tfrac{4}{3} \pi a b c, \qquad
        A \approx 4 \pi \left( \frac{(ab)^p + (ac)^p + (bc)^p}{3} \right)^{1/p}, \quad p = 1.6075,

    where the area :math:`A` is Knud Thomsen's approximation. :math:`\Psi` is 1 for a sphere and decreases towards 0 as
    the ellipsoid is stretched or flattened; it is dimensionless and does not depend on the unit of the data.

    Two entry points exist. ``process(frame, *, timestamp=None)`` takes an ``(N, 3)`` point cloud, fits the ellipsoid
    and returns the three outputs. ``process_axes(first_axis, second_axis, third_axis, *, timestamp=None)`` takes the
    three sizes of an ellipsoid directly (three positive scalars in the same unit, in any order) and returns only
    ``sphericity``; ``axis_ratio`` and ``radii`` are then not produced. The feature has no parameters and keeps no
    state.

    Notes
    -----
    **Outputs.** ``sphericity``: dimensionless, in (0, 1]. ``axis_ratio``: minor over major radius, in [0, 1]
    (point-cloud input only). ``radii``: ``(3,)`` fitted radii, major to minor, in the unit of the data (point-cloud
    input only).

    **Statuses.** ``INVALID_INPUT`` for fewer than 2 points, for NaN or infinite coordinates, and for a cloud whose
    major radius is below 1e-6; ``process_axes`` gives ``INVALID_INPUT`` unless the three sizes are positive and finite.

    References
    ----------
    :cite:`camurri2003recognizing`

    Examples
    --------
    >>> import numpy as np
    >>> from pyeyesweb.low_level import EllipsoidSphericity
    >>> cube = np.array([[x, y, z] for x in (0, 1) for y in (0, 1) for z in (0, 1)], dtype=float)
    >>> feature = EllipsoidSphericity()
    >>> print(f"{feature.process(cube).sphericity:.3f} {feature.process_axes(2.0, 1.0, 1.0).sphericity:.3f}")
    1.000 0.929
    """
    _core_class = core.motion.EllipsoidSphericity

    def _inputs(self) -> Inputs:
        return Inputs(points_input("points", None, "point cloud to fit an ellipsoid to"))

    def _schema(self) -> Schema:
        return Schema(Output("sphericity", doc="Wadell sphericity, 1 = sphere"),
                      Output("axis_ratio", doc="minor / major radius; point-cloud input only"),
                      Output("radii", 3, unit="<length>", doc="fitted radii, major to minor; point-cloud input only"))

    def _process(self, points: Any, timestamp: Optional[float]) -> Result:
        points = np.asarray(points, dtype=float)
        return self._to_result((len(points), *self._block.process_points(points)), timestamp)

    def _to_result(self, raw: Any, timestamp: Optional[float]) -> Result:
        size, sphericity, axis_ratio, radii = raw
        if size < 2:
            reason = "fewer than 2 points"
        elif radii[0] < _MIN_RADIUS or not np.isfinite(sphericity):
            reason = "no extent, or NaN / infinite coordinates"
        else:
            reason = ""
        return self._result(status=Status.INVALID_INPUT if reason else Status.OK, reason=reason,
                           sphericity=sphericity, axis_ratio=axis_ratio, radii=np.asarray(radii, dtype=float), timestamp=timestamp)

    def process_axes(self, first_axis: float, second_axis: float, third_axis: float, *, timestamp: Optional[float] = None) -> Result:
        """Sphericity of an ellipsoid given by its three sizes (the EyesWeb input); see the class documentation."""
        valid = all(np.isfinite(size) and size > 0 for size in (first_axis, second_axis, third_axis))
        return self._result(status=Status.OK if valid else Status.INVALID_INPUT,
                           reason="" if valid else "the sizes must be positive and finite",
                           sphericity=self._block.process(first_axis, second_axis, third_axis), timestamp=timestamp)


__all__ = ["BoundingBoxFilledArea", "EllipsoidSphericity", "PointsDensity"]
