"""Layer 2, low-level features: quantities of a movement over up to about 0.5 s (kinematics, energy, shape,
symmetry, smoothness, shape, and the directness and non-planarity of a path)."""

from .kinematics import Kinematics
from .energy import KineticEnergy
from .contraction import BoundingBoxFilledArea, EllipsoidSphericity, PointsDensity
from .symmetry import Symmetry, TriangleSymmetry
from .smoothness import (
    SpectralArcLength, LogDimensionlessJerk, Harmonicity, SubmovementCount, CurvatureDispersion,
    CurvatureVelocityCorrelation
)
from .equilibrium import Equilibrium
from .direction_change import DirectionChange
from .shape import FilterContour, ContourCurvature, ConvexHull, BodyPartsFromCurvature
from .motion_noise import MotionNoiseDetector
from .directness import Directness
from .non_planarity import TrajectoryNonPlanarity, average_curvature_3d

__all__ = [
    "Kinematics", "KineticEnergy", "BoundingBoxFilledArea", "EllipsoidSphericity", "PointsDensity", "Symmetry",
    "TriangleSymmetry", "SpectralArcLength", "LogDimensionlessJerk", "Harmonicity", "SubmovementCount",
    "CurvatureDispersion", "CurvatureVelocityCorrelation", "Equilibrium", "DirectionChange", "FilterContour",
    "ContourCurvature", "ConvexHull", "BodyPartsFromCurvature", "MotionNoiseDetector",
    "Directness", "TrajectoryNonPlanarity", "average_curvature_3d"
]


def __dir__():
    return sorted(__all__)
