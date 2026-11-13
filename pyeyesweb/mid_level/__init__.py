"""Layer 3, mid-level features: amodal features of a gesture over 0.5-3 s (segments, suddenness, impulsivity, space occupation)."""

from .segmentation import GestureSegmenter

__all__ = [
    "GestureSegmenter",
]


def __dir__():
    return sorted(__all__)
