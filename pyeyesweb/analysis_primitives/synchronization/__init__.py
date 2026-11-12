"""Synchronization between signals, events and people."""

from .phase import PhaseLockingValue
from .correlation import PartialRecurrenceSynchronization, GeneralisedAutoCorrelation
from .events import (
    EventSynchronization, EventSynchronizationMECS, NonlinearInterdependence, SpikeSynchronization,
)
from .recurrence import RecurrencePlot, CrossRecurrencePlot

__all__ = [
    "PhaseLockingValue", "PartialRecurrenceSynchronization", "GeneralisedAutoCorrelation",
    "EventSynchronization", "EventSynchronizationMECS", "NonlinearInterdependence", "SpikeSynchronization",
    "RecurrencePlot", "CrossRecurrencePlot",
]


def __dir__():
    return sorted(__all__)
