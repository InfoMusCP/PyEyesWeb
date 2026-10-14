"""Analysis primitives: metrics applicable to any movement feature at any layer of the conceptual model
(complexity, rarity, rhythm, periodicity, signal events, synchronization)."""

from .complexity import SampleEntropy, CoarseGraining
from .rarity import Rarity
from .rhythm import BinaryPulsesRegularity
from .multi_scale_entropy import MultiScaleEntropy
from .periodicity import Periodicity
from .signal_events import ScalarPeakDetector
from .synchronization import (
    PhaseLockingValue, CorrelationsMatrix, PartialRecurrenceSynchronization, GeneralisedAutoCorrelation,
    EventSynchronization, EventSynchronizationMECS, NonlinearInterdependence, SpikeSynchronization,
    SequenceDetector, RecurrencePlot, CrossRecurrencePlot, TemporalSynchronization
)

__all__ = [
    "SampleEntropy", "CoarseGraining", "Rarity", "BinaryPulsesRegularity", "MultiScaleEntropy", "Periodicity",
    "ScalarPeakDetector", "PhaseLockingValue", "CorrelationsMatrix",
    "PartialRecurrenceSynchronization", "GeneralisedAutoCorrelation", "EventSynchronization",
    "EventSynchronizationMECS", "NonlinearInterdependence", "SpikeSynchronization", "SequenceDetector",
    "RecurrencePlot", "CrossRecurrencePlot", "TemporalSynchronization"
]
