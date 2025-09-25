import time
import threading
import numpy as np
from typing import Optional, Union


class SlidingWindow:
    """
    A thread-safe sliding window buffer for storing samples with timestamps.

    This class implements a circular buffer that maintains a fixed-size window
    of the most recent samples. When the buffer is full, new samples overwrite
    the oldest ones. Each sample is associated with a timestamp.

    Parameters
    ----------
    max_length : int
        Maximum number of samples the window can hold.
    n_columns : int
        Number of columns (features) in each sample.

    Attributes
    ----------
    _lock : threading.Lock
        Thread lock for thread-safe operations.
    _max_length : int
        Maximum capacity of the buffer.
    _n_columns : int
        Number of columns per sample.
    _buffer : np.ndarray
        Circular buffer storing the samples, shape (max_length, n_columns).
    _timestamp : np.ndarray
        Array storing timestamps for each sample, shape (max_length,).
    _start : int
        Index of the oldest sample in the buffer.
    _size : int
        Current number of samples in the buffer.

    Examples
    --------
    >>> window = SlidingWindow(max_length=100, n_columns=3)
    >>> window.append([1.0, 2.0, 3.0])
    >>> window.append(np.array([4.0, 5.0, 6.0]), timestamp=1234567890.0)
    >>> data, timestamps = window.to_array()
    >>> print(f"Buffer contains {len(window)} samples")
    """

    def __init__(self, max_length: int, n_columns: int):
        self._lock = threading.Lock()

        self._max_length = max_length
        self._n_columns = n_columns

        self._buffer = np.empty((max_length, n_columns), dtype=np.float32)
        self._timestamp = np.empty(max_length, dtype=np.float64)

        self._start = 0
        self._size = 0

    def append(self, samples: Union[np.ndarray, list], timestamp: Optional[float] = None) -> None:
        """
        Append a new sample to the sliding window.

        If the buffer is not full, the sample is added to the next available
        position. If the buffer is full, the oldest sample is overwritten.

        Parameters
        ----------
        samples : np.ndarray or list
            Sample data to append. Must have exactly n_columns elements.
        timestamp : float, optional
            Timestamp associated with the sample. If None, uses the current
            monotonic time.

        Raises
        ------
        TypeError
            If samples is not a numpy array or list.
        ValueError
            If the sample shape doesn't match the expected number of columns.

        Examples
        --------
        >>> window = SlidingWindow(max_length=10, n_columns=2)
        >>> window.append([1.0, 2.0])
        >>> window.append(np.array([3.0, 4.0]), timestamp=1234567890.0)
        """
        with self._lock:
            if not isinstance(samples, (np.ndarray, list)):
                raise TypeError("Expected sample should be of type np.ndarray or list.")

            value = np.asarray(samples, dtype=np.float32).reshape(-1)

            if value.shape[0] != self._n_columns:
                raise ValueError(f"Expected shape ({self._n_columns},), got {value.shape}")

            if timestamp is None:
                timestamp = time.monotonic()

            if self._size < self._max_length:
                idx = (self._start + self._size) % self._max_length
                self._size += 1
            else:
                idx = self._start
                self._start = (self._start + 1) % self._max_length

            self._buffer[idx] = value
            self._timestamp[idx] = timestamp

    def to_array(self) -> tuple[np.ndarray, np.ndarray]:
        """
        Return the current contents of the sliding window as arrays.

        The returned arrays contain samples and timestamps in chronological
        order, with the oldest sample first and the newest sample last.

        Returns
        -------
        samples : np.ndarray
            Array of shape (current_size, n_columns) containing all samples
            in the buffer in chronological order.
        timestamps : np.ndarray
            Array of shape (current_size,) containing timestamps corresponding
            to each sample in chronological order.

        Examples
        --------
        >>> window = SlidingWindow(max_length=5, n_columns=2)
        >>> window.append([1.0, 2.0])
        >>> window.append([3.0, 4.0])
        >>> samples, timestamps = window.to_array()
        >>> print(samples.shape)  # (2, 2)
        >>> print(timestamps.shape)  # (2,)
        """
        indices = (self._start + np.arange(self._size)) % self._max_length
        return self._buffer[indices], self._timestamp[indices]

    def reset(self) -> None:
        """
        Reset the sliding window to empty state.

        Clears all samples and timestamps from the buffer and resets internal
        counters. The buffer arrays are filled with NaN values.

        Examples
        --------
        >>> window = SlidingWindow(max_length=10, n_columns=2)
        >>> window.append([1.0, 2.0])
        >>> print(len(window))  # 1
        >>> window.reset()
        >>> print(len(window))  # 0
        """
        self._start = 0
        self._size = 0
        self._buffer.fill(np.nan)
        self._timestamp.fill(np.nan)

    def is_full(self) -> bool:
        """
        Check if the sliding window buffer is at maximum capacity.

        Returns
        -------
        bool
            True if the buffer contains max_length samples, False otherwise.

        Examples
        --------
        >>> window = SlidingWindow(max_length=2, n_columns=1)
        >>> print(window.is_full())  # False
        >>> window.append([1.0])
        >>> window.append([2.0])
        >>> print(window.is_full())  # True
        """
        return self._size == self._max_length

    def __len__(self) -> int:
        """
        Return the current number of samples in the sliding window.

        Returns
        -------
        int
            Number of samples currently stored in the buffer.

        Examples
        --------
        >>> window = SlidingWindow(max_length=10, n_columns=2)
        >>> print(len(window))  # 0
        >>> window.append([1.0, 2.0])
        >>> print(len(window))  # 1
        """
        return self._size