"""Call contract of the synchronization features: declared inputs, process / run / reset, seconds, windows and
`_process_window`. Needs the compiled core (EYESWEB_CORE_PATH), else skipped."""
import os
import sys

import numpy as np
import pytest

if os.environ.get("EYESWEB_CORE_PATH"):
    sys.path.insert(0, os.environ["EYESWEB_CORE_PATH"])
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

pytest.importorskip("pyeyesweb._core", exc_type=ImportError)

from contract_suite import check_feature_contract  # noqa: E402
from pyeyesweb.analysis_primitives.synchronization import (  # noqa: E402
    PartialRecurrenceSynchronization, CorrelationsMatrix, CrossRecurrencePlot, EventSynchronization, NonlinearInterdependence,
    EventSynchronizationMECS, GeneralisedAutoCorrelation,
    RecurrencePlot, SequenceDetector, SpikeSynchronization, PhaseLockingValue,
    TemporalSynchronization)
from pyeyesweb.data_models import InputKind, Status  # noqa: E402

RNG = np.random.default_rng(0)
SAMPLE_COUNT = 80
TIMESTAMPS = np.arange(SAMPLE_COUNT) / 20.0
SIGNALS = np.stack([np.sin(2 * np.pi * TIMESTAMPS), np.sin(2 * np.pi * TIMESTAMPS + 0.7), RNG.standard_normal(SAMPLE_COUNT)], axis=1)
EVENTS_A = (RNG.random(SAMPLE_COUNT) > 0.8).astype(float)
EVENTS_B = (RNG.random(SAMPLE_COUNT) > 0.8).astype(float)
CLASSES_A = (RNG.random((SAMPLE_COUNT, 3)) > 0.8).astype(float)
CLASSES_B = (RNG.random((SAMPLE_COUNT, 3)) > 0.8).astype(float)
SPIKES = np.where(RNG.random((SAMPLE_COUNT, 2)) > 0.7, 1.0, -1.0)
IDS = RNG.integers(0, 3, SAMPLE_COUNT).astype(float)
MATRICES = np.stack([np.corrcoef(RNG.standard_normal((3, 10))) for _ in range(12)])

# name -> (factory, recordings)
CASES = {
    "PhaseLockingValue": (lambda: PhaseLockingValue(window=30, hop=10), (SIGNALS[:, 0], SIGNALS[:, 1])),
    "CorrelationsMatrix": (lambda: CorrelationsMatrix(window=20, hop=5, number_of_inputs=3), (SIGNALS,)),
    "GeneralisedAutoCorrelation": (lambda: GeneralisedAutoCorrelation(window=20, hop=10), (SIGNALS[:, 0],)),
    "PartialRecurrenceSynchronization": (lambda: PartialRecurrenceSynchronization(), (MATRICES,)),
    "EventSynchronization": (lambda: EventSynchronization(window=20, hop=20), (EVENTS_A, EVENTS_B)),
    "EventSynchronizationMECS": (lambda: EventSynchronizationMECS(window=20, hop=20), (CLASSES_A, CLASSES_B)),
    "NonlinearInterdependence": (lambda: NonlinearInterdependence(window=30, hop=10),
                                            (SIGNALS[:, 0], SIGNALS[:, 2])),
    "SpikeSynchronization": (lambda: SpikeSynchronization(window=20, hop=10), (SPIKES,)),
    "SequenceDetector": (lambda: SequenceDetector(), (IDS,)),
    "TemporalSynchronization": (lambda: TemporalSynchronization(thresholds=[0.5, 0.5, 0.5]), (np.abs(SIGNALS),)),
    "RecurrencePlot": (lambda: RecurrencePlot(window=10, hop=5, epsilon=0.5), (SIGNALS[:, :2],)),
    "CrossRecurrencePlot": (lambda: CrossRecurrencePlot(window=10, hop=5, epsilon=0.5),
                            (SIGNALS[:, :2], SIGNALS[:, 1:])),
}


@pytest.mark.parametrize("name", CASES)
def test_call_contract(name):
    factory, data = CASES[name]
    check_feature_contract(factory, *data)


@pytest.mark.parametrize("name", [name for name, (factory, _) in CASES.items() if hasattr(factory(), "window")])
def test_process_window_is_the_streamed_window(name):
    """The last sample of a stream of one window gives the same result as `_process_window` on that window."""
    factory, data = CASES[name]
    streamed = factory()
    window = streamed.window
    recordings = [np.asarray(series, float)[:window] for series in data]
    recordings = [recording.reshape(len(recording), -1) for recording in recordings]
    results = [streamed.process(*(result[index] for result in recordings)) for index in range(window)]
    assert [result.status for result in results[:-1]] == [Status.WARMING_UP] * (window - 1)
    direct = factory()._process_window(*(recording.T for recording in recordings))
    for output in direct.schema.names:
        np.testing.assert_array_equal(results[-1][output], direct[output])


def test_declared_inputs():
    assert PhaseLockingValue(window=10).inputs.names == ("first_signal", "second_signal")
    assert PhaseLockingValue(window=10).inputs["first_signal"].kind is InputKind.SAMPLE
    assert PartialRecurrenceSynchronization().inputs["correlations_matrix"].kind is InputKind.MATRIX
    assert CorrelationsMatrix(window=10, number_of_inputs=5).inputs["signals"].shape == (5,)
    assert EventSynchronization(window=10).inputs.names == ("first_signal", "second_signal")
    assert EventSynchronizationMECS(window=10, number_of_inputs=3).inputs.names == ("series1", "series2", "series3")
    assert SpikeSynchronization(window=10, number_of_inputs=4).inputs["trains"].shape == (4,)
    assert TemporalSynchronization(number_of_inputs=4).inputs["synchronization"].shape == (4,)
    assert CrossRecurrencePlot(window=10).inputs.names == ("first_series", "second_series")


def test_phase_locking_value_takes_two_signals():
    two = PhaseLockingValue(window=30).run(SIGNALS[:, 0], SIGNALS[:, 1])
    assert two.status[29] == Status.OK and two["phase_locking_value"][29] > 0.9
    with pytest.raises(ValueError):
        PhaseLockingValue(window=30).run(SIGNALS[:, 0])


def test_pars_takes_the_output_of_correlations_matrix():
    cpr = CorrelationsMatrix(window=40, hop=40, number_of_inputs=3).run(SIGNALS)
    matrices = [matrix for matrix, ok in zip(cpr["correlations_matrix"], cpr.ok) if ok]
    partial = PartialRecurrenceSynchronization().run(np.stack(matrices))
    assert len(partial) == len(matrices) and partial.ok.all()
