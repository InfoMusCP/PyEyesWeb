"""Layer 3, mid-level features: amodal features of a gesture over 0.5-3 s (segments, suddenness, impulsivity, space occupation).

No mid-level feature is in the early release: ``GestureSegmenter`` is held back until the noise test that belongs to it
(``MotionNoiseDetector``) is finished. It stays importable from ``pyeyesweb.mid_level.segmentation``.
"""

__all__: list = []


def __dir__():
    return sorted(__all__)
