"""Contraction and expansion analysis for body movement patterns.

This module provides optimized functions for analyzing contraction and expansion
of body configurations in 3D space. It computes geometric shape metrics, including
bounding box areas, convex hulls, and ellipsoid approximations, to track structural
changes relative to a movement baseline.
"""

import itertools
from dataclasses import dataclass
from typing import Optional

import numpy as np
from scipy.spatial import ConvexHull
from scipy.spatial import QhullError

from pyeyesweb.data_models.base import StaticFeature
from pyeyesweb.data_models.results import FeatureResult


@dataclass(slots=True)
class ContractionExpansionResult(FeatureResult):
    """Shared result contract for the contraction/expansion feature family.

    Attributes
    ----------
    contraction_index : float, optional
        The computed contraction index based on bounding box area.
    sphericity : float, optional
        The computed sphericity based on PCA ellipsoid fitting.
    points_density : float, optional
        The computed points density.
    """

    contraction_index: Optional[float] = (
        None  # TODO rename to something related to BoundingBoxFilledArea for clarity?
    )
    sphericity: Optional[float] = None
    points_density: Optional[float] = None


class BoundingBoxFilledArea(StaticFeature):
    r"""Computes the Contraction Index based on 3D Surface Area.

    Mathematical formulation involves computing the ratio:

    $$
    Index = \frac{Area_{hull}^2}{Area_{bbox}}
    $$

    where $Area_{hull}$ is the surface area of the 3D convex hull enclosing the points,
    and $Area_{bbox}$ is the surface area of the axis-aligned bounding box.

    !!! note
        This feature uses the Convex Hull area and the Axis-Aligned Bounding Box (AABB) area.

    Read more in the [User Guide](../../user_guide/theoretical_framework/low_level/contraction_expansion.md).
    """

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

    def compute(self, frame_data: np.ndarray) -> ContractionExpansionResult:
        """Compute the Contraction Index for a single frame.

        Parameters
        ----------
        frame_data : numpy.ndarray
            The motion data for a single frame.

        Returns
        -------
        ContractionExpansionResult
            The computed contraction index.
        """
        hull_area, hull_points = self._get_hull_data(frame_data)
        bbox_area, bbox_points = self._get_aabb_data(frame_data)

        index = (hull_area / bbox_area) if bbox_area > self.EPSILON else 0.0

        return ContractionExpansionResult(contraction_index=float(index))


class EllipsoidSphericity(StaticFeature):
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

    def compute(self, frame_data: np.ndarray) -> ContractionExpansionResult:
        """Compute the Sphericity based on fitted ellipsoid radii.

        Parameters
        ----------
        frame_data : numpy.ndarray
            The motion data for a single frame.

        Returns
        -------
        ContractionExpansionResult
            The computed sphericity metric.
        """
        radii, rotation = self._fit_ellipsoid_pca(frame_data)
        a, b, c = radii[0], radii[1], radii[2]

        if a < self.EPSILON:
            return ContractionExpansionResult(sphericity=0.0)

        return ContractionExpansionResult(sphericity=float(c / a))


class PointsDensity(StaticFeature):
    r"""Computes the Points Density (Dispersion) for a sequence of skeletal frames.

    $$
    D = \frac{1}{N} \sum_{i=1}^{N} \| X_i - \bar{X} \|
    $$

    where $N$ is the total number of points, $X_i$ is the 3D position of the $i$-th point,
    and $\bar{X}$ is the barycenter (mean position) of all points.

    Read more in the [User Guide](../../user_guide/theoretical_framework/low_level/contraction_expansion.md).
    """

    def compute(self, frame_data: np.ndarray) -> ContractionExpansionResult:
        """Compute the average distance of points from their barycenter.

        Parameters
        ----------
        frame_data : numpy.ndarray
            The motion data for a single frame.

        Returns
        -------
        ContractionExpansionResult
            The computed average points density.
        """
        if len(frame_data) == 0:
            return ContractionExpansionResult(points_density=0.0)

        barycenter = np.mean(frame_data, axis=0)
        distances = np.linalg.norm(frame_data - barycenter, axis=1)

        return ContractionExpansionResult(points_density=float(distances.mean()))
