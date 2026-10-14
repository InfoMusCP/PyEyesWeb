"""Contraction and expansion analysis for body movement patterns.

This module provides optimized functions for analyzing contraction and expansion
of body configurations in 3D space. It computes geometric shape metrics, including
bounding box areas, convex hulls, and ellipsoid approximations, to track structural
changes relative to a movement baseline.
"""

import itertools
import numpy as np
from scipy.spatial import ConvexHull
from scipy.spatial import QhullError

from pyeyesweb.catalog import Layer, describe
from legacy_base import StaticFeature
from pyeyesweb.data_models.results import Output, Schema, Status


@describe(Layer.LOW_LEVEL)
class BoundingBoxFilledAreaReference(StaticFeature):
    r"""Computes the Contraction Index based on 3D Surface Area.

    Mathematical formulation involves computing the ratio:

    $$
    Index = \frac{Area_{hull}}{Area_{bbox}}
    $$

    where $Area_{hull}$ is the surface area of the 3D convex hull enclosing the points,
    and $Area_{bbox}$ is the surface area of the axis-aligned bounding box.

    !!! note
        This feature uses the Convex Hull area and the Axis-Aligned Bounding Box (AABB) area.

    Read more in the [User Guide](../../user_guide/theoretical_framework/low_level/contraction_expansion.md).
    """

    OUTPUTS = Schema(Output("contraction_index", doc="Ratio of convex hull area to bounding box area."))

    EPSILON = 1e-6

    @staticmethod
    def _get_hull_data(points: np.ndarray) -> tuple[float, np.ndarray]:
        if len(points) < 4:
            return 0.0, np.array([])
        try:
            hull = ConvexHull(points)
            return hull.area, points[hull.vertices]
        except QhullError:
            # specifically catch geometric degeneracy (e.g., planar/collinear points)
            return 0.0, np.array([])

    @staticmethod
    def _get_aabb_data(points: np.ndarray) -> tuple[float, np.ndarray]:
        if len(points) == 0:
            return 0.0, np.array([])

        min_vals = np.min(points, axis=0)
        max_vals = np.max(points, axis=0)
        dims = max_vals - min_vals
        surface_area = 2 * (dims[0] * dims[1] + dims[0] * dims[2] + dims[1] * dims[2])

        corners = np.array(
            list(
                itertools.product(
                    [min_vals[0], max_vals[0]],
                    [min_vals[1], max_vals[1]],
                    [min_vals[2], max_vals[2]],
                )
            )
        )
        return surface_area, corners

    def compute(self, frame_data: np.ndarray) :
        """Compute the Contraction Index for a single frame.

        Parameters
        ----------
        frame_data : numpy.ndarray
            The motion data for a single frame.

        Returns
        -------
        Result
            Output `contraction_index` (float).
        """
        if len(frame_data) == 0:
            return self.no_output(Status.INVALID_INPUT, "empty frame")
        hull_area, hull_points = self._get_hull_data(frame_data)
        bbox_area, bbox_points = self._get_aabb_data(frame_data)

        index = (hull_area / bbox_area) if bbox_area > self.EPSILON else 0.0

        return self.result(contraction_index=float(index))


@describe(Layer.LOW_LEVEL)
class EllipsoidFitSphericityReference(StaticFeature):
    r"""Fits an ellipsoid to skeletal joints using PCA and computes shape metrics.

    Sphericity is defined as the ratio of the smallest to the largest radius:

    $$
    S = \frac{c}{a}
    $$

    where $c$ is the length of the shortest semi-axis (minor radius) and
    $a$ is the length of the longest semi-axis (major radius) of the fitted ellipsoid.

    !!! tip
        This metric is highly robust against rotation as it relies on PCA.

    Read more in the [User Guide](../../user_guide/theoretical_framework/low_level/contraction_expansion.md).
    """

    OUTPUTS = Schema(Output("sphericity", doc="Ratio of the smallest to the largest ellipsoid radius."))

    EPSILON = 1e-6

    @staticmethod
    def _fit_ellipsoid_pca(points: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        if len(points) < 2:
            return np.zeros(3), np.eye(3)

        centered = points - np.mean(points, axis=0)
        cov_matrix = np.cov(centered, rowvar=False)

        try:
            eigenvalues, eigenvectors = np.linalg.eigh(cov_matrix)
        except np.linalg.LinAlgError:
            return np.zeros(3), np.eye(3)

        radii = np.sqrt(np.abs(eigenvalues))
        sort_indices = np.argsort(radii)[::-1]

        return radii[sort_indices], eigenvectors[:, sort_indices]

    def compute(self, frame_data: np.ndarray) :
        """Compute the Sphericity based on fitted ellipsoid radii.

        Parameters
        ----------
        frame_data : numpy.ndarray
            The motion data for a single frame.

        Returns
        -------
        Result
            Output `sphericity` (float).
        """
        if len(frame_data) == 0:
            return self.no_output(Status.INVALID_INPUT, "empty frame")
        radii, rotation = self._fit_ellipsoid_pca(frame_data)
        major, minor = radii[0], radii[2]

        if major < self.EPSILON:
            return self.result(sphericity=0.0)

        return self.result(sphericity=float(minor / major))


__all__ = ["BoundingBoxFilledAreaReference", "EllipsoidFitSphericityReference"]
