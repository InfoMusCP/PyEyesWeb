"""Layer 1, physical signals and virtual sensors: frame-level, continuous data (skeletons, space, images) and the stream plumbing that feeds them (`TimeWindowSynchronizer`)."""

from .humanoid import (
    HumanoidSimulator, HumanoidOrientations, GenericModelOrientations, GenericModelSimulator, GenericModelPredictor,
    GenericModelEstimator, PointsPredictor, MassSpringModel, HUMANOID_JOINTS, HUMANOID_BONES
)
from .imaging import SilhouetteCentroids, SilhouetteBodyParts, Videogram
from .space import HitCellDetector
from .time_window_synchronizer import SynchronizedWindow, TimeWindowSynchronizer

__all__ = [
    "HumanoidSimulator", "HumanoidOrientations", "GenericModelOrientations",
    "GenericModelSimulator", "GenericModelPredictor", "GenericModelEstimator", "PointsPredictor", "MassSpringModel",
    "HUMANOID_JOINTS", "HUMANOID_BONES", "SilhouetteCentroids", "SilhouetteBodyParts", "Videogram",
    "HitCellDetector", "SynchronizedWindow", "TimeWindowSynchronizer"
]


def __dir__():
    return sorted(__all__)
