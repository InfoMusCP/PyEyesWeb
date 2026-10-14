"""Live parameter changes of the event and sequence blocks of `analysis_primitives.synchronization.events` (checks in
`tests/live_param_suite.py`).

* Event Sync: Tau and Weighted are LIVE (the queued events keep their counts); resetting every buffer is STRUCTURAL (read
  by Init()).
* MECS: the kernel (and sigma, mean) are LIVE; the number of series, Tau and the event classes are STRUCTURAL.
* SPIKE sync: stateless, every parameter takes effect on the next window and none restarts anything.
* Sequence detector: the inter-event time is LIVE; the sequence and the order are STRUCTURAL.

A parameter that is stored in the state (a countdown holds the threshold it was started with) is changed where that
state is still empty, so that "built with the new value" is comparable.
"""

import numpy as np
import pytest

from live_param_suite import check_invalid, check_live, check_structural, ids

from pyeyesweb.analysis_primitives.synchronization.events import (
    EventSynchronization, EventSynchronizationMECS, SequenceDetector, SpikeSynchronization
)

_rng = np.random.default_rng(5)
SAMPLE_COUNT = 120


def _train(offset, length=SAMPLE_COUNT, period=17):
    train = np.zeros(length)
    train[3 + offset::period] = 1
    return train


PAIRS = list(zip(_train(0), _train(2)))  # (ts1, ts2): an event of the second 2 samples after one of the first
SERIES = [([first], [second]) for first, second in PAIRS]  # (series1, series2), one event class each
SPIKES = [[-1.0 if _rng.random() < 0.7 else 1.0, -1.0 if _rng.random() < 0.7 else 1.0] for _ in range(SAMPLE_COUNT)]
SEQUENCE = [event for _ in range(SAMPLE_COUNT // 8) for event in (1, 0, 2, 0, 0, 0, 0, 0)]


LIVE = [
    (lambda: EventSynchronization(window=10, hop=10, tau=5), "tau", 8, PAIRS),
    (lambda: EventSynchronizationMECS(window=6, hop=6, tau=4, event_class_number=1), "kernel",
     "linear", SERIES),
    (lambda: SequenceDetector(sequence="1 2", inter_event_time=3), "inter_event_time", 4, SEQUENCE),
]
STRUCTURAL = [
    (lambda: EventSynchronization(window=10, hop=10, tau=5), "reset_every_buffer", True, PAIRS),
    (lambda: EventSynchronizationMECS(window=7, hop=7, tau=10), "event_class_number", 2, SERIES),
    (lambda: EventSynchronizationMECS(window=6, hop=6, tau=4, event_class_number=1), "tau", 6, SERIES),
    (lambda: SequenceDetector(sequence="1 2"), "sequence", "1 3", SEQUENCE),
]
INVALID = [
    (lambda: EventSynchronization(window=10, hop=10, tau=5), "tau", -1, PAIRS),
    (lambda: EventSynchronizationMECS(window=6, hop=6, tau=10), "tau", 0, SERIES),
    (lambda: SpikeSynchronization(window=8, hop=8, number_of_input_trains=2), "number_of_input_trains", 1, SPIKES),
    (lambda: SequenceDetector(sequence="1 2"), "sequence", "1 0", SEQUENCE),
]


def _param(rows):
    return pytest.mark.parametrize("factory, attr, value, recording", rows, ids=ids(rows))


@_param(LIVE)
def test_live_change_keeps_the_state(factory, attr, value, recording):
    check_live(factory, attr, value, recording)


@_param(STRUCTURAL)
def test_structural_change_restarts_and_says_so_once(factory, attr, value, recording):
    check_structural(factory, attr, value, recording)


@_param(INVALID)
def test_invalid_value_raises_and_changes_nothing(factory, attr, value, recording):
    check_invalid(factory, attr, value, recording)
