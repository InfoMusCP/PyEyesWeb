from abc import ABC, abstractmethod
import numpy as np

from pyeyesweb.data_models.results import FeatureResult
from pyeyesweb.data_models.sliding_window import SlidingWindow


class BaseLowLevelFeature(ABC):
    """The root class for all low-level features."""

    def __init__(self):
        pass

    @abstractmethod
    def __call__(self, data: SlidingWindow, **kwargs) -> FeatureResult:
        """Compute the feature. Must return a standardized FeatureResult."""
        pass


class StaticFeature(BaseLowLevelFeature):
    """
    Base class for features computed on a single frame (e.g., Posture, Density).
    """

    @abstractmethod
    def _compute_frame(self, frame_data: np.ndarray) -> FeatureResult:
        """
        The actual mathematical logic.
        Expects a 2D array of shape (N_nodes, N_dims).
        Must return a FeatureResult.
        """
        pass

    def __call__(self, data: SlidingWindow, **kwargs) -> FeatureResult:
        """
        The Smart API: Accepts a sliding window.
        Automatically extracts the latest frame and applies a safety net.
        """
        if len(data) == 0:
            return FeatureResult(is_valid=False)

        try:
            # Extract the 3D tensor and grab the very last frame (the newest one)
            tensor, _ = data.to_tensor()
            frame_data = tensor[-1]

            return self._compute_frame(frame_data)

        except Exception:
            # Catch mathematical or indexing errors without crashing the real-time loop
            return FeatureResult(is_valid=False)


class DynamicFeature(BaseLowLevelFeature):
    """
    Base class for features that require a time series (e.g., Smoothness, DirectionChange).
    """

    @abstractmethod
    def _compute_window(self, window_data: np.ndarray) -> FeatureResult:
        """
        The actual mathematical logic.
        Expects a 3D tensor of shape (Time, N_nodes, N_dims).
        Must return a FeatureResult.
        """
        pass

    def __call__(self, data: SlidingWindow, **kwargs) -> FeatureResult:
        """
        The Smart API: Accepts a sliding window and passes the full tensor downstream.
        """
        if len(data) == 0:
            return FeatureResult(is_valid=False)

        try:
            tensor, _ = data.to_tensor()
            return self._compute_window(tensor)

        except Exception:
            # Safety net for dynamic math calculations
            return FeatureResult(is_valid=False)
