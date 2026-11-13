"""Layer 3, mid-level features: amodal features of a gesture over 0.5-3 s (segments, suddenness, impulsivity, space occupation)."""

from .segmentation import GestureSegmenter, MotionDuration

__all__ = [
    "GestureSegmenter", "MotionDuration",
]


def __dir__():
    return sorted(__all__)
