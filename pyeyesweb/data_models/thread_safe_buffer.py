"""Thread-safe history buffer for PyEyesWeb.

This module provides a reusable thread-safe buffer implementation.
"""

import threading
from collections import deque
from typing import Any, List
import numpy as np


class ThreadSafeHistoryBuffer:
    """Thread-safe history buffer with deque backing.

    Parameters
    ----------
    maxlen : int
        Maximum size of the history buffer

    Examples
    --------
    >>> buffer = ThreadSafeHistoryBuffer(maxlen=100)
    >>> buffer.append(data)
    >>> history = buffer.get_history()
    >>> length = len(buffer)
    """

    def __init__(self, maxlen: int):
        """Initialize thread-safe history buffer.

        Parameters
        ----------
        maxlen : int
            Maximum size of the buffer
        """
        self._history = deque(maxlen=maxlen)
        self._lock = threading.RLock()

    def append(self, item: Any) -> None:
        """Thread-safely append item to history.

        Parameters
        ----------
        item : Any
            Item to append to the history buffer
        """
        with self._lock:
            self._history.append(item)

    def get_history(self) -> List[Any]:
        """Get a thread-safe copy of the history.

        Returns
        -------
        list
            Copy of the current history
        """
        with self._lock:
            return list(self._history)

    def get_array(self) -> np.ndarray:
        """Get history as numpy array (thread-safe).

        Returns
        -------
        np.ndarray
            History converted to numpy array
        """
        with self._lock:
            return np.array(list(self._history))

    def clear(self) -> None:
        """Clear the history buffer (thread-safe)."""
        with self._lock:
            self._history.clear()

    def __len__(self) -> int:
        """Get current size of buffer (thread-safe).

        Returns
        -------
        int
            Current number of items in buffer
        """
        with self._lock:
            return len(self._history)

    def __repr__(self) -> str:
        """String representation of buffer."""
        with self._lock:
            return f"ThreadSafeHistoryBuffer(maxlen={self._history.maxlen}, size={len(self._history)})"