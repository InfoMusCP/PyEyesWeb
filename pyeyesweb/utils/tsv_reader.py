"""TSV file reader for time-series data with real-time playback support.

This module provides a specialized TSV reader for motion capture and sensor data
files, supporting multiple reading modes including real-time playback simulation.
"""

import numpy as np
import time

class TSVReader:
    """TSV file reader with multiple reading modes for time-series data.

    Provides three reading modes:
    1. Block reading: Read fixed-size chunks of data
    2. Time-based access: Get data at specific time points
    3. Real-time iteration: Simulate real-time playback with timing delays

    Parameters
    ----------
    time_col : str, optional
        Name of the column containing time values (default: "Time").
    """

    def __init__(self, time_col="Time"):
        self.time_col = time_col
        self.headers = []
        self.data = None
        self.time_data = None
        self.index = 0
        self.prev_time = None
        self.filename = None

        self.n = None
        self.time_value = None
        self.use_time = False
        self.speed_factor = 1.0

    # ------------------- FILE NAME -------------------
    def _set_file_name(self, filename):
        self.filename = filename
        self.reset()
        self._load_file()

    # ------------------- TIME COLUMN -------------------
    def _set_time_column(self, time_col):
        self.time_col = time_col

    # ------------------- SIZE OF BLOCK -------------------
    def _set_block_size(self, block_size):
        self.n = block_size
        self.time_value = None
        self.use_time = False
        self.speed_factor = 1.0

    # ------------------- SPECIFIC TIME -------------------
    def _set_time_value(self, time_value):
        self.time_value = time_value
        self.n = None
        self.use_time = False
        self.speed_factor = 1.0

    # ------------------- REAL TIME READING -------------------
    def _set_use_time_and_speed(self, factor=1.0):
        self.use_time = True
        self.speed_factor = factor
        self.time_value = None
        self.n = None

    def _load_file(self):
        """Load TSV file quickly using np.loadtxt.

        Expects a TSV file with a header line starting with 'Frame'.
        """
        with open(self.filename, "r") as f:
            for i, line in enumerate(f):
                if line.startswith("Frame"):
                    header_idx = i
                    self.headers = line.strip().split("\t")
                    break
            else:
                raise ValueError("Header 'Frame...' not found")

        self.data = np.loadtxt(self.filename, delimiter="\t", skiprows=header_idx+1, dtype=float)
        if self.data.ndim == 1:
            self.data = self.data.reshape(1, -1)

        try:
            time_idx = self.headers.index(self.time_col)
        except ValueError:
            raise ValueError(f"Column '{self.time_col}' not found in headers")

        self.time_data = self.data[:, time_idx]

    def __call__(self,time_value=None):
        if time_value is not None:
            self.time_value = time_value
            return self._get_row_by_time()
        if self.n is not None:
            return self._get_n_rows()
        return self._iter_rows_gen()

    # ------------------- READ ROW BY TIME -------------------
    def _get_row_by_time(self):
        idx = np.searchsorted(self.time_data, self.time_value)
        if idx == len(self.time_data):
            idx -= 1
        elif idx > 0 and abs(self.time_data[idx-1] - self.time_value) < abs(self.time_data[idx] - self.time_value):
            idx -= 1
        return self.data[idx]

    # -------------------  READ BLOCK -------------------
    def _get_n_rows(self):
        start = self.index
        end = min(self.index + self.n, len(self.data))
        self.index = end
        return self.data[start:end]

    # ------------------- READ ROW BY ROW -------------------
    def _iter_rows_gen(self, chunk_size=1000):
        time_idx = self.headers.index(self.time_col)

        while self.index < len(self.data):
            end = min(self.index + chunk_size, len(self.data))
            chunk = self.data[self.index:end]

            for row in chunk:
                current_time = row[time_idx]

                if self.use_time and self.prev_time is not None:
                    delay = (current_time - self.prev_time) / self.speed_factor
                    if delay > 0:
                        self._sleep_accurate(delay)

                self.prev_time = current_time
                yield row

            self.index = end

    # ------------------- SLEEP -------------------
    def _sleep_accurate(self, delay_sec):
        """Sleep for the specified duration without burning CPU cycles.

        For delays >= 1ms, uses time.sleep() which yields the CPU to OS. For submillisecond delays, uses a hybrid approach for accuracy.
        """
        if delay_sec <= 0:
            return

        # For delays >= 1ms, use regular sleep (yields CPU)
        if delay_sec >= 0.001:
            time.sleep(delay_sec)
        else:
            # For sub-millisecond delays, minimize busy wait time
            # Sleep for most of the duration, then busy wait for precision
            if delay_sec > 0.0002:  # > 0.2ms
                time.sleep(delay_sec * 0.5)  # Sleep 50% of time

            # Brief busy-wait only for final precision
            target = time.perf_counter() + (delay_sec * 0.5 if delay_sec > 0.0002 else delay_sec)
            while time.perf_counter() < target:
                pass

    # ------------------- RESET -------------------
    def reset(self):
        self.index = 0
        self.prev_time = None
