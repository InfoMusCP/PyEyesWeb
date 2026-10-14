"""Contraction and expansion analysis for body movement patterns.

This module provides optimized functions for analyzing contraction and expansion
of body configurations in 3D space. It computes geometric shape metrics, including
bounding box areas, convex hulls and ellipsoid approximations, to track structural
changes relative to a movement baseline.
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
    r"""Computes the Contraction Index based on 3D Surface Area.

    Mathematical formulation involves computing the ratio:

    $$
    Index = \frac{Area_{hull}}{Area_{bbox}}
    $$

    where $Area_{hull}$ is the surface area of the 3D convex hull enclosing the points,
    and $Area_{bbox}$ is the surface area of the axis-aligned bounding box.

    !!! note
        This feature uses the Convex Hull area and the Axis-Aligned Bounding Box (AABB) area.

    Input: one frame per call, an `(N, 3)` array of points (other widths raise `ValueError`); stateless.
    `process(points, timestamp=None)` returns `contraction_index`; `Status.INVALID_INPUT` for a frame without points or
    whose bounding box has no extent (area at most `epsilon`, 1e-6), with fewer than 4 points or with coplanar points (the 3D
    hull is degenerate); the index is then empty (NaN).
    `timestamp` is the timestamp in seconds (`NaN` when not given).

    Read more in the [User Guide](../../user_guide/theoretical_framework/low_level/contraction_expansion.md).
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
    """EyesWeb PointsDensity3D.

    Input: one set of points per call, an `(N, 3)` array (named by `labels` when given, else by index: the labels do
    not enter the maths) or a dict `label -> (x, y, z)`. `process(points, timestamp=None)`; `timestamp` in seconds.

    Outputs `density`, a scalar when `output_dims` is MODULE (default) or a `(3,)` vector (x, y, z) when
    COMPONENT, and `centroid` `(3,)`. `INVALID_INPUT` ("no points") when the set holds no points.
    """
    _core_class = core.motion.PointsDensity

    def __init__(self, labels: Optional[Sequence[str]] = None, skeleton: Any = None, **params: Any):
        labels, params = with_skeleton(skeleton, labels, params)
        super().__init__(**params)
        self._labels = None if labels is None else tuple(labels)

    @property
    def labels(self) -> Optional[Tuple[str, ...]]:
        """The names of the points of array input (`None`: by index)."""
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
    """EyesWeb EllipsoidSphericity3D, and the sphericity of a point cloud.

    `process(points, timestamp=None)` (EXTENSION, not in EyesWeb) takes an `(N, 3)` point cloud, fits an ellipsoid by PCA
    (radii = sqrt of the covariance eigenvalues, sorted major to minor) and gives `sphericity` of the fitted radii,
    `axis_ratio` (minor / major radius) and `radii` `(3,)`. Fewer than 2 points, or a major radius below 1e-6,
    give `axis_ratio` 0 (and `sphericity` NaN when all radii are 0). Always `OK`.

    `process_axes(first_axis, second_axis, third_axis, timestamp=None)` (faithful EyesWeb input) takes the three ellipsoid sizes, three scalars of
    the same unit, and gives `sphericity`, the Wadell sphericity (1 for a sphere, < 1 otherwise); `axis_ratio`
    and `radii` are not produced (`valid` is `False`). It is a separate entry point because it receives
    something else than the declared `inputs`.

    `timestamp` is the timestamp in seconds (`NaN` when not given).
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
        """Sphericity of an ellipsoid of sizes `a`, `b`, `c` (the EyesWeb input); see the class documentation."""
        valid = all(np.isfinite(size) and size > 0 for size in (first_axis, second_axis, third_axis))
        return self._result(status=Status.OK if valid else Status.INVALID_INPUT,
                           reason="" if valid else "the sizes must be positive and finite",
                           sphericity=self._block.process(first_axis, second_axis, third_axis), timestamp=timestamp)


__all__ = ["BoundingBoxFilledArea", "EllipsoidSphericity", "PointsDensity"]
