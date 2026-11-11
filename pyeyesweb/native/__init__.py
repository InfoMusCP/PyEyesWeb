"""Native EyesWeb features: C++ port of EyesWeb XMI blocks, bound with nanobind.

The algorithms live in the compiled module ``eyw_core`` (sources in
``EyesWeb4/_standalone/eyw_core``); this sub-package exposes them with the
usual PyEyesWeb contracts (``SlidingWindow`` in, ``FeatureResult`` out).

``eyw_core`` is optional: this package always imports, and
:func:`is_available` tells whether the native features can be used.
Instantiating a feature without ``eyw_core`` raises an ``ImportError`` with
installation instructions.

Examples
--------
>>> from pyeyesweb.data_models import SlidingWindow
>>> from pyeyesweb.native import EventSynchronization
>>> es = EventSynchronization(tau=10, peak_buffer=15, peak_threshold=50.0)
>>> window = SlidingWindow(max_length=120, n_signals=2, n_dims=1)  # two hand speeds
>>> # ... window.append([left_speed, right_speed]) at every frame ...
>>> result = es(window)            # EventSynchronizationResult(Q=..., q=...)
"""

from ._backend import eyw_core_version, is_available
from .humanoid import BoneOrientations, BoneOrientationsResult, HumanoidFilter, HumanoidFilterResult
from .silhouette import (
    BodySubRegions,
    BodySubRegionsResult,
    SilhouetteCentroids,
    SilhouetteCentroidsResult,
    crop_to_blob,
    mask_from_body_index,
)
from .skeleton import (
    AZURE_TO_HUMANOID,
    HUMANOID_JOINTS,
    K4ABT_JOINTS,
    azure_to_humanoid_frame,
)
from .synchronization import (
    EventSynchronization,
    EventSynchronizationResult,
    NonlinearInterdependence,
    NonlinearInterdependenceResult,
    RecurrenceRate,
    RecurrenceRateResult,
    SpikeSynchronization,
    SpikeSynchronizationResult,
    extract_events,
    to_scalar_signals,
)

__all__ = [
    "is_available",
    "eyw_core_version",
    # synchronization
    "EventSynchronization",
    "EventSynchronizationResult",
    "SpikeSynchronization",
    "SpikeSynchronizationResult",
    "NonlinearInterdependence",
    "NonlinearInterdependenceResult",
    "RecurrenceRate",
    "RecurrenceRateResult",
    "extract_events",
    "to_scalar_signals",
    # humanoid
    "BoneOrientations",
    "BoneOrientationsResult",
    "HumanoidFilter",
    "HumanoidFilterResult",
    # silhouette
    "SilhouetteCentroids",
    "SilhouetteCentroidsResult",
    "BodySubRegions",
    "BodySubRegionsResult",
    "mask_from_body_index",
    "crop_to_blob",
    # skeleton conventions
    "HUMANOID_JOINTS",
    "K4ABT_JOINTS",
    "AZURE_TO_HUMANOID",
    "azure_to_humanoid_frame",
]
