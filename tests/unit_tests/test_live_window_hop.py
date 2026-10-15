"""`window` and `hop` of every windowed feature, changed on a running feature.

The base class `WindowedFeature` keeps the newest samples whatever the block, so `window` and `hop` are LIVE: no
"state reset" note, a window that shrinks gives a result at once, a window that grows warms up again. The exception is
`CurvatureVelocityCorrelation`, whose filters need the same length and overlap in consecutive windows (STRUCTURAL: they
restart). The memory of `Rarity(method="information")` and the buffers of `Videogram` and `ScalarPeakDetector` are
sized by their `window` in the core and restart (STRUCTURAL; see `test_live_parameters_motion.py`,
`_imaging.py` and `_trajectory_space_dance.py`).
"""

import numpy as np
import pytest

from live_param_suite import NOTE, feed

from pyeyesweb.analysis_primitives import (BinaryPulsesRegularity, CoarseGraining, CorrelationsMatrix, CrossRecurrencePlot,
                                           EventSynchronization, EventSynchronizationMECS, GeneralisedAutoCorrelation,
                                           MultiScaleEntropy, NonlinearInterdependence, Periodicity, PhaseLockingValue,
                                           Rarity, RecurrencePlot, SampleEntropy, SpikeSynchronization)
from pyeyesweb.data_models import Status
from pyeyesweb.low_level import (CurvatureVelocityCorrelation, DirectionChange, Harmonicity, LogDimensionlessJerk,
                                 SpectralArcLength, SubmovementCount)
from pyeyesweb.mid_level import Suddenness, SuddennessImpulsivity

_rng = np.random.default_rng(11)
HELD = 60  # samples fed before the change


def _frames(width, count=HELD + 80):
    return [(_rng.random(width),) for _ in range(count)]


def _pairs(count=HELD + 80):
    return [(_rng.random(1), _rng.random(1)) for _ in range(count)]


def _events(count=HELD + 80):
    return [(_rng.random(1) > 0.8) * 1.0 for _ in range(count)], [(_rng.random(1) > 0.8) * 1.0 for _ in range(count)]


EVENT_PAIRS = [(first, second) for first, second in zip(*_events())]

# (factory, recording): `hop` of the factory is 5 unless the block needs another.
FREE = [
    (lambda: SampleEntropy(window=30, hop=5), _frames(1)),
    (lambda: CoarseGraining(window=30, hop=5, factor=2), _frames(1)),
    (lambda: BinaryPulsesRegularity(window=30, hop=5), _frames(1)),
    (lambda: Periodicity(window=30, hop=5), _frames(1)),
    (lambda: MultiScaleEntropy(window=3100, hop=5), _frames(1, 3400)),
    (lambda: DirectionChange(window=30, hop=5), _frames(3)),
    (lambda: Suddenness(window=30, hop=5), _frames(3)),
    (lambda: SuddennessImpulsivity(window=30, hop=5), _frames(3)),
    (lambda: SpectralArcLength(window=30, hop=5, sampling_rate=50.0), _frames(1)),
    (lambda: LogDimensionlessJerk(window=30, hop=5, sampling_rate=50.0), _frames(1)),
    (lambda: Harmonicity(window=30, hop=5, sampling_rate=50.0), _frames(1)),
    (lambda: SubmovementCount(window=30, hop=5, sampling_rate=50.0), _frames(1)),
    (lambda: Rarity(window=30, hop=5, method="mode_distance"), _frames(1)),
    (lambda: CorrelationsMatrix(window=30, hop=5, number_of_inputs=3), _frames(3)),
    (lambda: GeneralisedAutoCorrelation(window=30, hop=5), _frames(1)),
    (lambda: RecurrencePlot(window=30, hop=5), _frames(1)),
    (lambda: CrossRecurrencePlot(window=30, hop=5), _pairs()),
    (lambda: NonlinearInterdependence(window=30, hop=5), _pairs()),
    (lambda: PhaseLockingValue(window=60, hop=5, low_frequency=1.0, high_frequency=10.0, sampling_rate=100.0), _pairs()),
    (lambda: SpikeSynchronization(window=30, hop=5, number_of_inputs=2), _frames(2)),
]
LONG = {MultiScaleEntropy: 3200}  # the samples fed before the change


def _held(feature):
    return LONG.get(type(feature), HELD)


@pytest.mark.parametrize("factory, recording", FREE, ids=[row[0]().__class__.__name__ for row in FREE])
def test_window_and_hop_are_live(factory, recording):
    feature = factory()
    held = _held(feature)
    feed(feature, recording[:held])
    feature.hop = 1
    assert feature.process(*recording[held]).status != Status.WARMING_UP
    feature.window = feature.window - 10 if feature.window > 40 else 25  # shorter than what the buffer holds
    shrunk = feature.process(*recording[held + 1])
    assert NOTE not in shrunk.reason and shrunk.status != Status.WARMING_UP
    feature.window = feature.window + 30
    grown = feed(feature, recording[held + 2:held + 12])
    assert all(NOTE not in result.reason for result in grown)
    assert grown[0].status == Status.WARMING_UP  # the new window is longer than the samples held


@pytest.mark.parametrize("feature, recording, window", [
    (EventSynchronization(window=10, tau=5), EVENT_PAIRS, 20),
    (EventSynchronizationMECS(window=6, tau=4, number_of_event_classes=1), [([a[0]], [b[0]]) for a, b in EVENT_PAIRS], 12),
], ids=["EventSynchronization", "EventSynchronizationMECS"])
def test_window_of_accumulating_blocks_is_live_through_configure(feature, recording, window):
    feed(feature, recording[:HELD])
    feature.configure(window=window, hop=window)  # hop must stay equal to window
    after = feed(feature, recording[HELD:HELD + 3 * window])
    assert all(NOTE not in result.reason for result in after)
    assert [result.status for result in after[:window]].count(Status.OK) == 1  # held 0 of the new window at the change


def test_window_change_of_smoothness_restarts_its_filters_for_hop_too():
    feature = CurvatureVelocityCorrelation(window=24, hop=12, sampling_rate=25.0)
    feed(feature, _frames(1)[:HELD])
    feature.hop = 6
    assert NOTE in feature.process(_rng.random(1)).reason
