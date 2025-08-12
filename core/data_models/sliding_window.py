import time
import threading
import numpy as np
from typing import Optional, Union


class SlidingWindow:

    def __init__(self, max_length: int, n_columns: int):
        self._lock = threading.Lock()

        self._max_length = max_length
        self._n_columns = n_columns

        self._buffer = np.empty((max_length, n_columns), dtype=np.float32)
        self._timestamp = np.empty(max_length, dtype=np.float64)

        self._start = 0
        self._size = 0

    def append(self, samples: Union[np.ndarray, list], timestamp: Optional[float] = None) -> None:
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
        indices = (self._start + np.arange(self._size)) % self._max_length
        return self._buffer[indices], self._timestamp[indices]

    def reset(self) -> None:
        self._start = 0
        self._size = 0
        self._buffer.fill(np.nan)
        self._timestamp.fill(np.nan)

    def is_full(self) -> bool:
        return self._size == self._max_length

    def __len__(self) -> int:
        return self._size
