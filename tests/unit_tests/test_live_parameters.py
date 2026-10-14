"""Parameters change on a running feature without losing its state, unless they are structural.

Pilot blocks; every other area keeps its table in `test_live_parameters_<area>.py` (checks in `tests/live_param_suite.py`). A row is
`(factory, setter_name, new_value, recording)`; `recording` is a list of what `process` receives, one item per call.

* LIVE: the parameter does not enter the state. Changing it at sample K gives, from K on, what a feature built with
  the new value from the start gives, and the status sequence of an unchanged control.
* STRUCTURAL: the original block reads it in Init(). The state restarts and the next result says so, once.
* INVALID: a value the core rejects. It raises, and the feature goes on as if nothing had happened.
"""

import numpy as np
import pytest

from live_param_suite import NOTE, check_invalid, check_live, check_structural, feed, ids

from pyeyesweb.analysis_primitives.complexity import SampleEntropy
from pyeyesweb.data_models import Status
from pyeyesweb.low_level.energy import KineticEnergy
from pyeyesweb.low_level.smoothness import CurvatureVelocityCorrelation

_rng = np.random.default_rng(7)

SIGNAL = [[value] for value in np.cumsum(_rng.normal(size=120))]
HAND = [{"hand": tuple(point)} for point in np.cumsum(_rng.normal(size=(120, 3)), axis=0)]


def kinetic(**params):
    return KineticEnergy(weights={"hand": 1.0},
                         **params)


LIVE = [
    (lambda: kinetic(), "weights", {"hand": 3.0}, HAND),
    (lambda: SampleEntropy(window=20, embedding_dimension=3), "tolerance", 0.8, SIGNAL),
    (lambda: SampleEntropy(window=20, embedding_dimension=3, tolerance=0.8), "tolerance", None, SIGNAL),
    (lambda: SampleEntropy(window=20, embedding_dimension=3), "relative_tolerance", 0.5, SIGNAL),
    (lambda: CurvatureVelocityCorrelation(window=24, hop=12), "upper_limit", 0.5, SIGNAL),
]
STRUCTURAL = [
    (lambda: kinetic(), "input_mode", "velocity", HAND),
    (lambda: CurvatureVelocityCorrelation(window=24, hop=12), "filter_window_length", 7, SIGNAL),
]
INVALID = [
    (lambda: kinetic(input_mode="velocity", reference_point=""), "reference_point",
     "torso", HAND),
    (lambda: SampleEntropy(window=20, embedding_dimension=3), "embedding_dimension", 0, SIGNAL),
    (lambda: SampleEntropy(window=20, embedding_dimension=3), "relative_tolerance", 0, SIGNAL),
    (lambda: CurvatureVelocityCorrelation(window=24, hop=12), "filter_window_length", 8, SIGNAL),
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


def test_window_change_keeps_the_newest_samples():
    feature = SampleEntropy(window=20, embedding_dimension=3)
    feed(feature, SIGNAL[:30])
    feature.window = 10
    assert feature.process(SIGNAL[30]).status == Status.OK
    feature.window = 40  # holds 10 samples: 30 more
    statuses = [result.status for result in feed(feature, SIGNAL[31:71])]
    assert statuses[:29] == [Status.WARMING_UP] * 29 and statuses[29] == Status.OK


def test_hop_change_keeps_the_state():
    feature = SampleEntropy(window=20, hop=5, embedding_dimension=3)
    feed(feature, SIGNAL[:30])
    feature.hop = 2
    assert (feature.window, feature.hop) == (20, 2)
    assert feature.process(SIGNAL[30]).status == Status.OK


def test_window_change_of_smoothness_restarts_its_filters_and_says_so():
    feature = CurvatureVelocityCorrelation(window=24, hop=12)
    feed(feature, SIGNAL[:60])
    feature.window = 30
    assert NOTE in feature.process(SIGNAL[60]).reason
    later = feed(feature, SIGNAL[61:100])
    assert all(NOTE not in result.reason for result in later)
    assert any(result.status == Status.OK for result in later)  # the filters were rebuilt for the new length and overlap
