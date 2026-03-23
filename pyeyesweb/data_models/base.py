"""Core abstractions for the feature extraction pipeline.

This module defines the [BaseFeature][pyeyesweb.data_models.base.BaseFeature]
abstract base class and its primary specializations:
[StaticFeature][pyeyesweb.data_models.base.StaticFeature] and
[DynamicFeature][pyeyesweb.data_models.base.DynamicFeature].
"""

from abc import ABC, abstractmethod
import numpy as np

from .results import FeatureResult
from .sliding_window import SlidingWindow


class BaseFeature(ABC):
    """The root abstract class for all PyEyesWeb features.

    Defines the dual-API structure for all computational components:
    
    1. **Streaming API (`__call__`)**: Evaluates a `SlidingWindow`.
    2. **Pure Math API (`compute`)**: Evaluates a raw NumPy array.
    """

    def __init__(self):
        pass

    @abstractmethod
    def __call__(self, data: SlidingWindow) -> FeatureResult:
        """The Streaming API: Compute the feature using a SlidingWindow.

        Handles state and buffering for real-time applications by processing
        the contents of the provided window.

        Parameters
        ----------
        data : SlidingWindow
            The circular buffer containing motion samples.

        Returns
        -------
        FeatureResult
            The computed feature result.
        """
        pass

    @abstractmethod
    def compute(self, data: np.ndarray) -> FeatureResult:
        """The Pure Math API: Compute the feature from a raw NumPy array.

        Stateless and designed for composition or offline data science.

        Parameters
        ----------
        data : numpy.ndarray
            Raw motion data array.

        Returns
        -------
        FeatureResult
            The computed feature result.
        """
        pass


class StaticFeature(BaseFeature):
    """Base class for features computed on a single frame.

    Examples include posture analysis, spatial density, or instantaneous
    geometric properties.
    """

    @abstractmethod
    def compute(self, data: np.ndarray) -> FeatureResult:
        """The actual mathematical logic for a single frame.

        Parameters
        ----------
        data : numpy.ndarray of shape (N_nodes, N_dims)
            Snapshot of motion data for a single point in time.

        Returns
        -------
        FeatureResult
            Must return a specialized `FeatureResult` for the feature.
        """
        pass

    def __call__(self, data: SlidingWindow, **kwargs) -> FeatureResult:
        """The Streaming API for static features.

        Automatically extracts the latest frame from the `SlidingWindow` and
        delegates to the `compute` method.

        Parameters
        ----------
        data : SlidingWindow
            Circular buffer containing the data.
        **kwargs
            Additional arguments passed to `compute`.

        Returns
        -------
        FeatureResult
            Result for the newest frame. Returns `FeatureResult(is_valid=False)`
            if the window is empty.
        """
        if len(data) == 0:
            return FeatureResult(is_valid=False)

        # Extract the 3D tensor and grab the very last frame (the newest one)
        tensor, _ = data.to_tensor()
        frame_data = tensor[-1]

        # Delegate to the pure math API. Exceptions will naturally bubble up!
        return self.compute(frame_data)


class DynamicFeature(BaseFeature):
    """Base class for features that require a time-series window.

    Examples include smoothness, direction change, or any feature involving
    temporal variations.
    """

    @abstractmethod
    def compute(self, data: np.ndarray) -> FeatureResult:
        """The actual mathematical logic for a time-series window.

        Parameters
        ----------
        data : numpy.ndarray of shape (Time, N_nodes, N_dims)
            3D tensor of motion data within the window.

        Returns
        -------
        FeatureResult
            Must return a specialized `FeatureResult` for the feature.
        """
        pass

    def __call__(self, data: SlidingWindow) -> FeatureResult:
        """The Streaming API for dynamic features.

        Extracts the full chronological tensor from the `SlidingWindow` and
        passes it to the `compute` method.

        Parameters
        ----------
        data : SlidingWindow
            Circular buffer containing the time-series data.

        Returns
        -------
        FeatureResult
            Result for the window. Returns `FeatureResult(is_valid=False)`
            if the window is empty.
        """
        if len(data) == 0:
            return FeatureResult(is_valid=False)

        # Extract the 3D tensor
        tensor, _ = data.to_tensor()

        # Delegate to the pure math API. Exceptions will naturally bubble up!
        return self.compute(tensor)
