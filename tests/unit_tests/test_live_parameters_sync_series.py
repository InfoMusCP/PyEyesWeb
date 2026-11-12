"""Live parameter changes of the series and signal blocks of `analysis_primitives.synchronization` (checks in
`tests/_support/live_param_suite.py`).

* Recurrence plots, cross recurrence plots, interdependence, tau estimator, phase locking value: stateless in the
  core, every parameter is LIVE (the windows buffered by the feature are kept).
* Correlations matrix: `number_of_inputs` is STRUCTURAL (read by Init(): number of inputs and size of the output).
* Generalised auto correlation: epsilon and lag are LIVE; output_type and max_lag are STRUCTURAL.
* Temporal synchronization: p, m, thresholds are LIVE; number_of_inputs is STRUCTURAL.
"""

import numpy as np
import pytest

from live_param_suite import check_invalid, check_live, check_structural, ids

from pyeyesweb.analysis_primitives.synchronization.correlation import (
    GeneralisedAutoCorrelation
)
from pyeyesweb.analysis_primitives.synchronization.phase import PhaseLockingValue
from pyeyesweb.analysis_primitives.synchronization.recurrence import CrossRecurrencePlot, RecurrencePlot
from pyeyesweb.analysis_primitives.synchronization.events import NonlinearInterdependence

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
]
STRUCTURAL = [
    (lambda: GeneralisedAutoCorrelation(window=30), "max_lag", 5, SIGNAL),
    (lambda: GeneralisedAutoCorrelation(window=30), "output_type", "scalar", SIGNAL),
]
INVALID = [
    (lambda: RecurrencePlot(window=20, epsilon=0.5), "epsilon", -1.0, SIGNAL),
    (lambda: CrossRecurrencePlot(window=20, epsilon=0.5), "epsilon", -1.0, PAIRS),
    (lambda: NonlinearInterdependence(window=30, neighbours=2), "neighbours", -1, SCALARS),
    (lambda: PhaseLockingValue(window=60, low_frequency=1.0, high_frequency=10.0, sampling_rate=100.0), "low_frequency", 20.0, SCALARS),
    (lambda: GeneralisedAutoCorrelation(window=30, epsilon=0.1), "epsilon", -1.0, SIGNAL),
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
