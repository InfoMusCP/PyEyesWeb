from abc import ABC, abstractmethod
import numpy as np

from .results import FeatureResult
from .sliding_window import SlidingWindow


class BaseFeature(ABC):
    """The root class for all low-level features."""

    def __init__(self):
        pass

    @abstractmethod
    def __call__(self, data: SlidingWindow) -> FeatureResult:
        """
        The Streaming API:
        Compute the feature using a SlidingWindow.
        Handles state and buffering for real-time applications.
        """
        pass

    @abstractmethod
    def compute(self, data: np.ndarray) -> FeatureResult:
        """
        The Pure Math API:
        Compute the feature directly from a raw NumPy array.
        Stateless and designed for composition or offline data science.
        """
        pass


class StaticFeature(BaseFeature):
    """
    Base class for features computed on a single frame (e.g., Posture, Density).
    """

    @abstractmethod
    def compute(self, data: np.ndarray) -> FeatureResult:
        """
        The actual mathematical logic.
        Expects a 2D array of shape (N_nodes, N_dims).
        Must return a FeatureResult.
        """
        pass

    def __call__(self, data: SlidingWindow, **kwargs) -> FeatureResult:
        """
        The Streaming API: Accepts a sliding window.
        Automatically extracts the latest frame and delegates to the math API.
        """
        if len(data) == 0:
            return FeatureResult(is_valid=False)

        # Extract the 3D tensor and grab the very last frame (the newest one)
        tensor, _ = data.to_tensor()
        frame_data = tensor[-1]

        # Delegate to the pure math API. Exceptions will naturally bubble up!
        return self.compute(frame_data)


class DynamicFeature(BaseFeature):
    """
    Base class for features that require a time series (e.g., Smoothness, DirectionChange).
    """

    @abstractmethod
    def compute(self, data: np.ndarray) -> FeatureResult:
        """
        The actual mathematical logic.
        Expects a 3D tensor of shape (Time, N_nodes, N_dims).
        Must return a FeatureResult.
        """
        pass

    def __call__(self, data: SlidingWindow) -> FeatureResult:
        """
        The Streaming API: Accepts a sliding window and passes the full tensor downstream.
        """
        if len(data) == 0:
            return FeatureResult(is_valid=False)

        # Extract the 3D tensor
        tensor, _ = data.to_tensor()

        # Delegate to the pure math API. Exceptions will naturally bubble up!
        return self.compute(tensor)
