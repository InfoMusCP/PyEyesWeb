"""Live parameter changes of the series and signal blocks of `analysis_primitives.synchronization` (checks in
`tests/_support/live_param_suite.py`).

* Recurrence plots, cross recurrence plots, interdependence, tau estimator, phase locking value: stateless in the
  core, every parameter is LIVE (the windows buffered by the feature are kept).
* Correlations matrix: `number_of_inputs` is STRUCTURAL (read by Init(): number of inputs and size of the output).
* Generalised auto correlation: epsilon, tau, tau_min are LIVE; output_type and tau_spread are STRUCTURAL.
* Temporal synchronization: p, m, thresholds are LIVE; number_of_inputs is STRUCTURAL.
"""

import numpy as np
import pytest

from live_param_suite import NOTE, check_invalid, check_live, check_structural, feed, ids

from pyeyesweb.analysis_primitives.synchronization.correlation import (
    CorrelationsMatrix, GeneralisedAutoCorrelation
)
from pyeyesweb.analysis_primitives.synchronization.phase import PhaseLockingValue
from pyeyesweb.analysis_primitives.synchronization.recurrence import CrossRecurrencePlot, RecurrencePlot
from pyeyesweb.analysis_primitives.synchronization.temporal import TemporalSynchronization
from pyeyesweb.analysis_primitives.synchronization.events import NonlinearInterdependence
from pyeyesweb.data_models import Status

_rng = np.random.default_rng(11)
SAMPLE_COUNT = 120

SIGNAL = [list(point) for point in np.cumsum(_rng.normal(size=(SAMPLE_COUNT, 2)), axis=0)]
PAIRS = [(first, second) for first, second in zip(SIGNAL, SIGNAL[::-1])]
SCALARS = [(first[0], second[0]) for first, second in PAIRS]
QUADS = [list(_rng.uniform(0, 2, size=4)) for _ in range(60)]
TRIPLES = [list(_rng.uniform(0, 2, size=3)) for _ in range(60)]
FOURS = [list(_rng.normal(size=4)) for _ in range(60)]
THREES = [list(_rng.normal(size=3)) for _ in range(60)]

LIVE = [
    (lambda: RecurrencePlot(window=20), "epsilon", 1.5, SIGNAL),
    (lambda: CrossRecurrencePlot(window=20), "epsilon", 1.5, PAIRS),
    (lambda: NonlinearInterdependence(window=30, neighbours=2), "neighbours", 3, SCALARS),
    (lambda: PhaseLockingValue(window=60, low_frequency=1.0, high_frequency=10.0, sampling_rate=100.0), "low_frequency", 2.0, SCALARS),
    (lambda: GeneralisedAutoCorrelation(window=30), "epsilon", 2.0, SIGNAL),
    (lambda: TemporalSynchronization(thresholds=[1, 1, 1]), "thresholds", [0.5, 1.5, 1], TRIPLES * 2),
]
STRUCTURAL = [
    (lambda: GeneralisedAutoCorrelation(window=30), "tau_spread", 5, SIGNAL),
    (lambda: GeneralisedAutoCorrelation(window=30), "output_type", "scalar", SIGNAL),
    (lambda: TemporalSynchronization(number_of_inputs=4), "number_of_inputs", 3, QUADS + TRIPLES),
]
INVALID = [
    (lambda: RecurrencePlot(window=20, epsilon=0.5), "epsilon", -1.0, SIGNAL),
    (lambda: CrossRecurrencePlot(window=20, epsilon=0.5), "epsilon", -1.0, PAIRS),
    (lambda: NonlinearInterdependence(window=30, neighbours=2), "neighbours", -1, SCALARS),
    (lambda: PhaseLockingValue(window=60, low_frequency=1.0, high_frequency=10.0, sampling_rate=100.0), "low_frequency", 20.0, SCALARS),
    (lambda: CorrelationsMatrix(window=10, number_of_inputs=3), "number_of_inputs", 1, THREES),
    (lambda: GeneralisedAutoCorrelation(window=30, epsilon=0.1), "epsilon", -1.0, SIGNAL),
    (lambda: TemporalSynchronization(number_of_inputs=3), "number_of_inputs", 0, TRIPLES * 2),
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


def test_correlations_matrix_number_of_inputs_restarts_its_buffer_and_says_so_once():
    feature = CorrelationsMatrix(window=10, number_of_inputs=4)
    feed(feature, FOURS[:30])
    feature.number_of_inputs = 3
    after = feed(feature, THREES)
    assert [result.status for result in after[:9]] == [Status.WARMING_UP] * 9 and after[9].status == Status.OK
    assert NOTE in after[0].reason and all(NOTE not in result.reason for result in after[1:])
    assert after[9].correlations_matrix.shape == (3, 3)


def test_generalised_auto_correlation_set_tau_min_is_live_and_keeps_the_window():
    feature, control = GeneralisedAutoCorrelation(window=30), GeneralisedAutoCorrelation(window=30, tau_min=3)
    feed(feature, SIGNAL[:50])
    feature.set_tau_min(3)
    assert feature.tau_min == 3
    assert feed(feature, SIGNAL[50:]) == feed(control, SIGNAL)[50:]
