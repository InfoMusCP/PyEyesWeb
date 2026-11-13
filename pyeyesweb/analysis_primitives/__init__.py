"""Analysis primitives: metrics applicable to any movement feature at any layer of the conceptual model
(complexity, rarity, rhythm, periodicity, signal events, synchronization)."""

from .complexity import SampleEntropy
from .rarity import Rarity
from .rhythm import BinaryPulsesRegularity
from .multi_scale_entropy import MultiScaleEntropy
from .periodicity import Periodicity
from .signal_events import ScalarPeakDetector
from .synchronization import PhaseLockingValue, PartialRecurrenceSynchronization, GeneralisedAutoCorrelation, EventSynchronization, EventSynchronizationMECS, RecurrencePlot, CrossRecurrencePlot

__all__ = [
    "SampleEntropy", "Rarity", "BinaryPulsesRegularity", "MultiScaleEntropy", "Periodicity", "ScalarPeakDetector",
    "PhaseLockingValue", "PartialRecurrenceSynchronization", "GeneralisedAutoCorrelation", "EventSynchronization",
    "EventSynchronizationMECS", "RecurrencePlot", "CrossRecurrencePlot",
]


def __dir__():
    return sorted([*__all__, "synchronization"])
