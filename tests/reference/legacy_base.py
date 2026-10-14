"""The former `BaseFeature` / `StaticFeature` / `DynamicFeature` (`compute` and `__call__(SlidingWindow)`), kept only so
that the preserved reference implementations in this directory still run. Not part of the library."""

from abc import ABC, abstractmethod

import numpy as np

from pyeyesweb.data_models.base import OutputsMixin
from pyeyesweb.data_models.results import Result, Status
SlidingWindow = object  # the removed 1.x buffer, named only in annotations


class BaseFeature(OutputsMixin, ABC):
    """The root abstract class for all PyEyesWeb features.

    Defines the dual-API structure for all computational components:

    1. **Streaming API (`__call__`)**: Evaluates a `SlidingWindow`.
    2. **Pure Math API (`compute`)**: Evaluates a raw NumPy array.

    Both return a [Result][pyeyesweb.data_models.results.Result] following the schema in `feature.outputs`.
    """

    def __init__(self):
        pass

    @abstractmethod
    def __call__(self, data: SlidingWindow) -> Result:
        """The Streaming API: Compute the feature using a SlidingWindow.

        Handles state and buffering for real-time applications by processing
        the contents of the provided window.

        Parameters
        ----------
        data : SlidingWindow
            The circular buffer containing motion samples.

        Returns
        -------
        Result
            The computed feature result; `status` is `WARMING_UP` while the window is empty.
        """
        pass

    @abstractmethod
    def compute(self, data: np.ndarray) -> Result:
        """The Pure Math API: Compute the feature from a raw NumPy array.

        Stateless and designed for composition or offline data science.

        Parameters
        ----------
        data : numpy.ndarray
            Raw motion data array.

        Returns
        -------
        Result
            The computed feature result.
        """
        pass


class StaticFeature(BaseFeature):
    """Base class for features computed on a single frame.

    Examples include posture analysis, spatial density, or instantaneous
    geometric properties.
    """

    @abstractmethod
    def compute(self, data: np.ndarray) -> Result:
        """The actual mathematical logic for a single frame.

        Parameters
        ----------
        data : numpy.ndarray of shape (N_nodes, N_dims)
            Snapshot of motion data for a single point in time.

        Returns
        -------
        Result
            Built with `self._result(...)`.
        """
        pass

    def __call__(self, data: SlidingWindow, **kwargs) -> Result:
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
        Result
            Result for the newest frame, stamped with that frame's timestamp. `Status.WARMING_UP` if the window
            is empty.
        """
        if len(data) == 0:
            return self._no_output(Status.WARMING_UP, "empty window")

        # Extract the 3D tensor and grab the very last frame (the newest one)
        tensor, timestamps = data.to_tensor()

        # Delegate to the pure math API. Exceptions will naturally bubble up!
        return self.compute(tensor[-1], **kwargs).with_time(float(timestamps[-1]))


class DynamicFeature(BaseFeature):
    """Base class for features that require a time-series window.

    Examples include smoothness, direction change, or any feature involving
    temporal variations.
    """

    @abstractmethod
    def compute(self, data: np.ndarray) -> Result:
        """The actual mathematical logic for a time-series window.

        Parameters
        ----------
        data : numpy.ndarray of shape (Time, N_nodes, N_dims)
            3D tensor of motion data within the window.

        Returns
        -------
        Result
            Built with `self._result(...)`; `Status.WARMING_UP` while the window is too short.
        """
        pass

    def __call__(self, data: SlidingWindow, **kwargs) -> Result:
        """The Streaming API for dynamic features.

        Extracts the full chronological tensor from the `SlidingWindow` and
        passes it to the `compute` method.

        Parameters
        ----------
        data : SlidingWindow
            Circular buffer containing the time-series data.
        **kwargs
            Additional arguments passed to `compute`.

        Returns
        -------
        Result
            Result for the window, stamped with the newest timestamp. `Status.WARMING_UP` if the window is empty.
        """
        if len(data) == 0:
            return self._no_output(Status.WARMING_UP, "empty window")

        tensor, timestamps = data.to_tensor()

        # Delegate to the pure math API. Exceptions will naturally bubble up!
        return self.compute(tensor, **kwargs).with_time(float(timestamps[-1]))
