"""Synchronization family: Event Sync and MECS without overlap, SPIKE input conventions, non-finite input, minimum windows."""


import numpy as np
import pytest

from pyeyesweb.analysis_primitives.synchronization import (
    PartialRecurrenceSynchronization, CorrelationsMatrix, CrossRecurrencePlot, NonlinearInterdependence,
    EventSynchronization, EventSynchronizationMECS, GeneralisedAutoCorrelation, RecurrencePlot, SpikeSynchronization, PhaseLockingValue
)
from pyeyesweb.data_models.results import Status

RNG = np.random.default_rng(3)


@pytest.mark.parametrize("cls", [EventSynchronization, EventSynchronizationMECS])
def test_hop_is_window_and_overlap_is_refused(cls):
    """Both accumulate across windows (#48: the pairwise Event Sync did not refuse overlap, whose samples it counted twice)."""
    assert cls(window=20).hop == 20
    assert cls(window=20, hop=20).hop == 20
    with pytest.raises(ValueError, match="overlapping"):
        cls(window=20, hop=10)
    feature = cls(window=20)
    with pytest.raises(ValueError, match="overlapping"):
        feature.hop = 5
    with pytest.raises(ValueError, match="overlapping"):
        feature.window = 30
    feature.configure(window=30, hop=30)
    assert (feature.window, feature.hop) == (30, 30)


def test_event_synchronization_streams_non_overlapping_windows():
    feature = EventSynchronization(window=10)
    events = (RNG.random((30, 2)) > 0.7).astype(float)
    assert [feature.process(*pair).status for pair in events].count(Status.OK) == 3


def test_mecs_streams_non_overlapping_windows():
    feature = EventSynchronizationMECS(window=10)
    events = (RNG.random((30, 2, 3)) > 0.7).astype(float)
    statuses = [feature.process(pair[0], pair[1]).status for pair in events]
    assert statuses.count(Status.OK) == 3


def test_spike_binary_accepts_both_event_conventions():
    zero_one = (RNG.random((2, 40)) > 0.6).astype(float)
    signed = np.where(zero_one > 0, 1.0, -1.0)
    unsigned = SpikeSynchronization(window=40)._process_window(zero_one)
    second = SpikeSynchronization(window=40)._process_window(signed)
    assert unsigned.degree == second.degree and unsigned.distance == second.distance
    np.testing.assert_array_equal(unsigned.profile, second.profile)
    streamed = SpikeSynchronization(window=40)
    results = [streamed.process(zero_one[:, index]) for index in range(40)]
    assert results[-1].degree == unsigned.degree


def test_spike_timings_process_raises_and_process_window_works():
    feature = SpikeSynchronization(window=3, mode="timings")
    with pytest.raises(TypeError, match="_process_window"):
        feature.process([1.0, 2.0])
    assert feature._process_window(np.array([[1.0, 5.0, 9.0], [1.0, 5.0, 9.5]])).valid["degree"]


def test_pars_non_finite_matrix_is_invalid_input_and_must_be_square():
    result = PartialRecurrenceSynchronization().process(np.full((3, 3), np.nan))
    assert result.status is Status.INVALID_INPUT and result.reason
    assert PartialRecurrenceSynchronization().process(np.zeros((0, 0))).status is Status.INVALID_INPUT
    with pytest.raises(ValueError, match="square"):
        PartialRecurrenceSynchronization().process(np.ones((2, 3)))
    assert PartialRecurrenceSynchronization().process(np.eye(3)).status is Status.OK


def test_warming_up_correlations_matrix_into_pars():
    cpr, pars = CorrelationsMatrix(window=5, number_of_inputs=2), PartialRecurrenceSynchronization()
    for _ in range(5):
        row = cpr.process(RNG.standard_normal(2))
        if row.status is Status.OK:
            assert pars.process(row.correlations_matrix).status is Status.OK
        else:
            assert pars.process(row.correlations_matrix).status is Status.INVALID_INPUT


@pytest.mark.parametrize("factory, series", [
    (lambda: CorrelationsMatrix(window=8, number_of_inputs=2), (2, 8)),
    (lambda: RecurrencePlot(window=8), (2, 8)),
    (lambda: GeneralisedAutoCorrelation(window=20), (1, 20)),
])
def test_non_finite_window_is_invalid_input(factory, series):
    data = RNG.standard_normal(series)
    data[0, 2] = np.nan
    result = factory()._process_window(data)
    assert result.status is Status.INVALID_INPUT and result.reason
    data[0, 2] = np.inf
    assert factory()._process_window(data).status is Status.INVALID_INPUT


def test_phase_locking_value_non_finite_window_is_invalid_input():
    first_series, second_series = RNG.standard_normal((2, 1, 8))
    first_series[0, 2] = np.nan
    result = PhaseLockingValue(window=8)._process_window(first_series, second_series)
    assert result.status is Status.INVALID_INPUT and result.reason
    first_series[0, 2] = np.inf
    assert PhaseLockingValue(window=8)._process_window(first_series, second_series).status is Status.INVALID_INPUT


def test_cross_recurrence_non_finite_is_invalid_input():
    first_series, second_series = RNG.standard_normal((2, 6)), RNG.standard_normal((2, 6))
    second_series[1, 1] = np.nan
    assert CrossRecurrencePlot(window=6)._process_window(first_series, second_series).status is Status.INVALID_INPUT


def test_interdependence_window_must_exceed_k():
    with pytest.raises(ValueError, match="window"):
        NonlinearInterdependence(window=2)
    with pytest.raises(ValueError, match="window"):
        NonlinearInterdependence(window=5, neighbours=5)
    feature = NonlinearInterdependence(window=5, neighbours=3)
    with pytest.raises(ValueError, match="window"):
        feature.neighbours = 5
    with pytest.raises(ValueError, match="window"):
        feature.window = 3
    assert feature.neighbours == 3 and feature.window == 5
    feature.neighbours = 4
    assert feature._process_window(RNG.random((1, 5)), RNG.random((1, 5))).status is Status.OK


def test_generalised_auto_correlation_minimum_window_follows_the_core():
    with pytest.raises(ValueError, match="window"):
        GeneralisedAutoCorrelation(window=3)
    assert GeneralisedAutoCorrelation(window=4)._process_window(RNG.random((1, 4))).status is Status.OK
    with pytest.raises(ValueError, match="window"):
        GeneralisedAutoCorrelation(window=9, tau_min=3)
    GeneralisedAutoCorrelation(window=10, tau_min=3)._process_window(RNG.random((1, 10)))
    GeneralisedAutoCorrelation(window=2, output_type="scalar")


def test_set_tau_min_is_kept_by_a_rebuilt_block():
    feature = GeneralisedAutoCorrelation(window=30)
    feature.set_tau_min(3)
    assert feature.tau_min == 3
    feature._invalidate_block()
    result = feature._process_window(RNG.random((1, 30)))
    assert result.taus[0] == 3
    with pytest.raises(ValueError, match="window"):
        feature.set_tau_min(30)


def test_correlations_matrix_needs_two_samples():
    with pytest.raises(ValueError, match="window"):
        CorrelationsMatrix(window=1)


def test_synchronization_filter_needs_a_long_enough_window():
    with pytest.raises(ValueError, match="window"):
        PhaseLockingValue(window=27, low_frequency=1.0, high_frequency=10.0, sampling_rate=100.0)
    feature = PhaseLockingValue(window=28, low_frequency=1.0, high_frequency=10.0, sampling_rate=100.0)
    assert (feature.low_frequency, feature.high_frequency, feature.sampling_rate) == (1.0, 10.0, 100.0)
    with pytest.raises(ValueError, match="window"):
        feature.window = 20
    unfiltered = PhaseLockingValue(window=10)
    unfiltered.sampling_rate, unfiltered.high_frequency = 100.0, 10.0  # a band needs both edges: not filtering yet
    with pytest.raises(ValueError, match="window"):
        unfiltered.low_frequency = 1.0
    assert unfiltered.low_frequency is None
    unfiltered.window = 40
    unfiltered.low_frequency = 1.0
    assert (unfiltered.low_frequency, unfiltered.high_frequency) == (1.0, 10.0)
    assert unfiltered._process_window(*RNG.standard_normal((2, 1, 40))).status is Status.OK


def test_importing_the_package_does_not_load_scipy():
    import subprocess
    import sys
    code = "import sys, pyeyesweb.analysis_primitives; sys.exit('scipy' in sys.modules)"
    assert subprocess.run([sys.executable, "-c", code]).returncode == 0

