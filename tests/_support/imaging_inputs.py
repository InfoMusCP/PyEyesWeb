"""Deterministic inputs of the imaging tests: a synthetic silhouette, video frames and pulse windows.

The frozen reference `tests/data/imaging_reference.npz` holds the output of the colleague's independent port (`eyw_core`) on
exactly these inputs (see `test_imaging_reference.py`), so they must not change.
"""

import numpy as np


def silhouette(height: int = 240, width: int = 320, shift: int = 0) -> np.ndarray:
    """A synthetic body: head, trunk, arms (a horizontal bar) and two legs, as a 0 / 255 `uint8` mask. `shift` moves it right."""
    rows, columns = np.mgrid[:height, :width]
    body = np.zeros((height, width), bool)
    body |= (columns - 160 - shift) ** 2 / 18 ** 2 + (rows - 40) ** 2 / 22 ** 2 <= 1                       # head
    body |= (abs(columns - 160 - shift) <= 28) & (rows >= 60) & (rows <= 140)                              # trunk
    body |= (abs(rows - 75) <= 7) & (columns >= 80 + shift) & (columns <= 240 + shift)                     # arms
    body |= (abs(columns - 147 - shift) <= 9) & (rows > 140) & (rows <= 225)                               # left leg
    body |= (abs(columns - 173 - shift - (rows - 140) * 0.3) <= 9) & (rows > 140) & (rows <= 225)          # right leg
    return (body * 255).astype(np.uint8)


def crop(mask: np.ndarray):
    """The mask cropped to its bounding box, and the `(x, y)` of the box's corner in the frame."""
    rows, columns = np.nonzero(mask)
    return mask[rows.min():rows.max() + 1, columns.min():columns.max() + 1].copy(), (int(columns.min()), int(rows.min()))


_rng = np.random.default_rng(3)
VIDEO_COLOUR = [(_rng.random((6, 9, 3)) * _rng.choice([30, 255])).astype(np.uint8) for _ in range(12)]
VIDEO_GRAY = [(_rng.random((6, 9)) * 255).astype(np.uint8) for _ in range(12)]


def _pulse_windows():
    rng = np.random.default_rng(5)
    windows = []
    for _ in range(30):
        length = int(rng.integers(4, 24))
        window = np.zeros(length)
        if rng.random() < 0.6:
            window[int(rng.integers(0, 3))::int(rng.integers(1, 5))] = 1
            if rng.random() < 0.4:
                window[int(rng.integers(0, length))] = 1
        else:
            window[rng.random(length) < 0.3] = 1
        windows.append(window)
    return windows


PULSE_WINDOWS = _pulse_windows()
