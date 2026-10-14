"""Layer 3, mid-level features: amodal features of a gesture over 0.5-3 s (segments, suddenness, impulsivity, directness and non-planarity of a path, space occupation)."""

from .segmentation import GestureSegmenter, MotionDuration
from .suddenness import Suddenness
from .impulsivity import SuddennessImpulsivity, ContractionImpulsivity
from .directness import Directness
from .non_planarity import TrajectoryNonPlanarity, average_curvature_3d
from .space_occupation import PositionDependingPotentials, RegionDependingPotentials

__all__ = [
    "GestureSegmenter", "MotionDuration", "Suddenness", "SuddennessImpulsivity", "ContractionImpulsivity",
    "Directness", "TrajectoryNonPlanarity", "average_curvature_3d", "PositionDependingPotentials", "RegionDependingPotentials"
]


def __dir__():
    return sorted(__all__)
