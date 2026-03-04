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
    """Shared result contract for the contraction/expansion feature family."""
    contraction_index: Optional[float] = None  # TODO rename to something related to BoundingBoxFilledArea for clarity?
    sphericity: Optional[float] = None
    points_density: Optional[float] = None


class BoundingBoxFilledArea(StaticFeature):
    """Computes the Contraction Index based on 3D Surface Area."""

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

        corners = np.array(list(itertools.product(
            [min_vals[0], max_vals[0]],
            [min_vals[1], max_vals[1]],
            [min_vals[2], max_vals[2]]
        )))
        return surface_area, corners

    def compute(self, frame_data: np.ndarray) -> ContractionExpansionResult:
        hull_area, hull_points = self._get_hull_data(frame_data)
        bbox_area, bbox_points = self._get_aabb_data(frame_data)

        index = (hull_area ** 2 / bbox_area) if bbox_area > self.EPSILON else 0.0

        return ContractionExpansionResult(contraction_index=float(index))


class EllipsoidSphericity(StaticFeature):
    """Fits an ellipsoid to skeletal joints using PCA and computes shape metrics."""

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
        radii, rotation = self._fit_ellipsoid_pca(frame_data)
        a, b, c = radii[0], radii[1], radii[2]

        if a < self.EPSILON:
            return ContractionExpansionResult(sphericity=0.0)

        return ContractionExpansionResult(sphericity=float(c / a))


class PointsDensity(StaticFeature):
    """Computes the Points Density (Dispersion) for a sequence of skeletal frames."""

    def compute(self, frame_data: np.ndarray) -> ContractionExpansionResult:
        if len(frame_data) == 0:
            return ContractionExpansionResult(points_density=0.0)

        barycenter = np.mean(frame_data, axis=0)
        distances = np.linalg.norm(frame_data - barycenter, axis=1)

        return ContractionExpansionResult(points_density=float(distances.mean()))
