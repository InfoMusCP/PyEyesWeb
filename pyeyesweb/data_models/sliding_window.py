import time
import threading
import numpy as np
from typing import Optional, Union
from pyeyesweb.utils.validators import validate_integer


class SlidingWindow:
    """
    A thread-safe sliding window buffer for storing samples with timestamps.

    This class implements a circular buffer that maintains a fixed-size window
    of the most recent samples. When the buffer is full, new samples overwrite
    the oldest ones. The internal data shape is strictly maintained as a 3D tensor:
    (Time, Nodes, Dimensions).

    Parameters
    ----------
    max_length : int
        Maximum number of samples (time frames) the window can hold.
    n_signals : int, optional
        Number of entities tracked (e.g., 1 for a single signal, 17 for skeleton joints). Default is 1.
    n_dims : int, optional
        Number of dimensions per node (e.g., 1 for speed, 3 for 3D coordinates). Default is 1.

    Examples
    --------
    >>> window = SlidingWindow(max_length=100, n_signals=1, n_dims=3)
    >>> window.append([1.0, 2.0, 3.0])
    >>> window.append([4.0, 5.0, 6.0], timestamp=1234567890.0)
    >>> data, timestamps = window.to_tensor()
    >>> print(window.is_full) # False
    """

    def __init__(self, max_length: int, n_signals: int = 1, n_dims: int = 1):
        self._max_length = validate_integer(max_length, 'max_length', min_val=1, max_val=10_000_000)
        self._n_signals = validate_integer(n_signals, 'n_signals', min_val=1, max_val=1000)
        self._n_dims = validate_integer(n_dims, 'n_dims', min_val=1, max_val=10_000)

        self._lock = threading.RLock()

        # Initialize with NaNs to ensure algorithms don't process garbage memory
        self._buffer = np.full((self._max_length, self._n_signals, self._n_dims), np.nan, dtype=np.float32)
        self._timestamp = np.full(self._max_length, np.nan, dtype=np.float64)

        self._start = 0
        self._size = 0

    @property
    def max_length(self) -> int:
        """Maximum capacity of the buffer."""
        return self._max_length

    @max_length.setter
    def max_length(self, value: int):
        if value <= 0:
            raise ValueError("max_length must be positive.")
        if value != self._max_length:
            old_max_length = self._max_length
            self._max_length = value
            self._resize(old_max_length)

    @property
    def n_signals(self) -> int:
        """The number of entities (signals) tracked by the window."""
        return self._n_signals

    @property
    def n_dims(self) -> int:
        """The number of dimensions per node."""
        return self._n_dims

    @property
    def is_full(self) -> bool:
        """Check if the sliding window buffer is at maximum capacity."""
        with self._lock:
            return self._size == self._max_length

    def __len__(self) -> int:
        """Return the current number of samples in the sliding window."""
        with self._lock:
            return self._size

    def __repr__(self) -> str:
        """Return a concise representation showing state and shape."""
        data, _ = self.to_tensor()
        return f"SlidingWindow(size={self._size}/{self._max_length}, shape=(T, {self._n_signals}, {self._n_dims}))\ndata=\n{data}"

    def _resize(self, old_max_length: int):
        with self._lock:
            indices = (self._start + np.arange(self._size)) % old_max_length
            old_data = self._buffer[indices].copy()
            old_timestamps = self._timestamp[indices].copy()

            new_buffer = np.full((self._max_length, self._n_signals, self._n_dims), np.nan, dtype=np.float32)
            new_timestamps = np.full(self._max_length, np.nan, dtype=np.float64)

            keep = min(len(old_data), self._max_length)
            if keep > 0:
                new_buffer[:keep, :, :] = old_data[-keep:, :, :]
                new_timestamps[:keep] = old_timestamps[-keep:]

            self._buffer = new_buffer
            self._timestamp = new_timestamps
            self._start = 0
            self._size = keep

    def append(self, sample: Union[list, np.ndarray, float, int], timestamp: Optional[float] = None) -> None:
        """
        Append a new sample to the sliding window.

        Accepts scalars, flat lists, or shaped numpy arrays, and automatically
        reshapes them to fit the configured (n_nodes, n_dims) structure.
        """
        sample_arr = np.asarray(sample, dtype=np.float32)

        try:
            sample_reshaped = sample_arr.reshape(self._n_signals, self._n_dims)
        except ValueError:
            raise ValueError(
                f"Cannot reshape input of size {sample_arr.size} into "
                f"expected shape ({self._n_signals} nodes, {self._n_dims} dims)."
            )

        with self._lock:
            if timestamp is None:
                timestamp = time.monotonic()

            if self._size < self._max_length:
                idx = (self._start + self._size) % self._max_length
                self._size += 1
            else:
                idx = self._start
                self._start = (self._start + 1) % self._max_length

            self._buffer[idx] = sample_reshaped
            self._timestamp[idx] = timestamp

    def to_tensor(self) -> tuple[np.ndarray, np.ndarray]:
        """
        Return the contents as a 3D tensor of shape (Time, Nodes, Dimensions).

        Returns
        -------
        tensor : np.ndarray
            Array of shape (current_size, n_nodes, n_dims) in chronological order.
        timestamps : np.ndarray
            Array of shape (current_size,) containing corresponding timestamps.
        """
        with self._lock:
            indices = (self._start + np.arange(self._size)) % self._max_length
            return self._buffer[indices].copy(), self._timestamp[indices].copy()

    def to_flat_array(self) -> tuple[np.ndarray, np.ndarray]:
        """
        Return the contents flattened to a 2D shape of (Time, Nodes * Dimensions).

        Returns
        -------
        flat_array : np.ndarray
            Array of shape (current_size, n_nodes * n_dims).
        timestamps : np.ndarray
            Array of shape (current_size,) containing corresponding timestamps.
        """
        tensor, timestamps = self.to_tensor()
        if tensor.size == 0:
            return np.empty((0, self._n_signals * self._n_dims), dtype=np.float32), timestamps

        flat_array = tensor.reshape(self._size, self._n_signals * self._n_dims)
        return flat_array, timestamps

    def reset(self) -> None:
        """Reset the sliding window to an empty state, filling buffers with NaNs."""
        with self._lock:
            self._start = 0
            self._size = 0
            self._buffer.fill(np.nan)
            self._timestamp.fill(np.nan)