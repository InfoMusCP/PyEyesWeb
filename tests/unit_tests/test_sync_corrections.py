"""Event synchronisation blocks after the corrections of 2026-10-14 (see docs/developer/porting_status.md).

The expected numbers are those of the independent port `eyw_core` (cross-checked by the maintainers), which agree with
the core after the corrections on every input tried (unweighted and weighted Event Sync, MECS v2, SPIKE sync in both
modes, SequenceDetector, TemporalSynchronization).
"""
import os
import sys

import numpy as np
import pytest

if os.environ.get("EYESWEB_CORE_PATH"):
    sys.path.insert(0, os.environ["EYESWEB_CORE_PATH"])

pytest.importorskip("pyeyesweb._core", exc_type=ImportError)

from pyeyesweb.analysis_primitives.synchronization import (  # noqa: E402
    EventSynchronization, EventSynchronizationMECS, SequenceDetector, SpikeSynchronization, TemporalSynchronization)


def pair(lag, length=100, tau=3, weighted=False):
    """Event Sync of a train with an event every 10 samples and the same train delayed by `lag` samples."""
    first = np.zeros(length)
    first[10:90:10] = 1
    second = np.roll(first, lag) if lag else first.copy()
    block = EventSynchronization(window=length, hop=length, tau=tau, weighted=weighted)
    result = block._process_window(first[None], second[None])
    return float(result.synchronization), float(result.delay)


@pytest.mark.parametrize("lag,expected", [(-4, 0.0), (-3, 1.0), (-2, 1.0), (-1, 1.0), (0, 1.0), (1, 1.0), (2, 1.0), (3, 1.0), (4, 0.0)])
def test_event_sync_accepts_the_lags_up_to_tau(lag, expected):
    """0 < lag <= tau (EyesWeb: 1 <= lag <= tau - 1: with tau = 3 a lag of 3 gave 0)."""
    assert pair(lag)[0] == expected
    assert np.sign(pair(lag)[1]) == (np.sign(lag) if expected else 0)  # q > 0 when the first series leads


def test_event_sync_tau_one_accepts_a_lag_of_one():
    assert pair(1, tau=1) == (1.0, 1.0) and pair(2, tau=1)[0] == 0.0


@pytest.mark.parametrize("lag,expected", [(1, 1.0), (2, 2 / 3), (3, 1 / 3), (4, 0.0)])
def test_weighted_event_sync_is_one_at_lag_one_and_one_over_tau_at_lag_tau(lag, expected):
    """Weight 1 - (lag - 1) / tau (EyesWeb: integer division, 0 for every lag inside the window)."""
    assert pair(lag, weighted=True)[0] == pytest.approx(expected, abs=1e-12)
    assert pair(-lag, weighted=True)[1] == pytest.approx(-expected, abs=1e-12)


def test_mecs_of_identical_series_is_one_whatever_the_number_of_events():
    """Pair normalisation min(1, S / sqrt(m_i m_j)) (EyesWeb: S / (m_i m_j): 1, 0.5, 0.25 for m = 1, 2, 4)."""
    for events in (1, 2, 4):
        series = np.zeros((1, 60))
        series[0, [5, 20, 40, 50][:events]] = 1
        block = EventSynchronizationMECS(window=60, hop=60, number_of_inputs=2, number_of_event_classes=1, tau=5)
        assert block._process_window(series, series.copy()).synchronization[0] == pytest.approx(1.0, abs=1e-12)


def test_mecs_pair_value_is_the_geometric_mean_normalisation_clamped_to_one():
    first = np.zeros((2, 40))
    second = np.zeros((2, 40))
    first[0, [10, 20]] = 1          # class 0: two events, S = 2 against one event within tau -> 2 / sqrt(2), clamped to 1
    second[0, 10] = 1
    first[1, [5, 25]] = 1           # class 1: 2 events each, one coincident pair: S = 1 -> 1 / sqrt(4) = 0.5
    second[1, [5, 33]] = 1
    block = EventSynchronizationMECS(window=40, hop=40, number_of_inputs=2, number_of_event_classes=2, tau=3)
    assert block._process_window(first, second).synchronization == pytest.approx([1.0 / np.sqrt(2), 0.5], abs=1e-12)


def spike_trains(first, second, length=60):
    trains = np.full((2, length), -1.0)
    trains[0, first] = 1
    trains[1, second] = 1
    return trains


def test_spike_sync_averages_over_all_spikes_of_all_trains():
    """a = [10, 20, 30], b = [10, 21, 45]: coincident a10, b10, a20, b21 of 6 spikes (EyesWeb: 3 / 5 distinct positions)."""
    result = SpikeSynchronization(window=60, hop=60)._process_window(spike_trains([10, 20, 30], [10, 21, 45]))
    assert result.degree == pytest.approx(4 / 6, abs=1e-12) and result.distance == pytest.approx(2 / 6, abs=1e-12)
    assert result.profile[10] == 1.0  # the profile keeps one value per sample
    timings = SpikeSynchronization(window=3, hop=3, mode="timings").process(np.array([[10.0, 20, 30], [10, 21, 45]]))
    assert timings.degree == pytest.approx(4 / 6, abs=1e-12)
    assert SpikeSynchronization(window=4, hop=4, mode="timings").process(
        np.array([[1.0, 2, 3, 4], [1, 2, 3.5, 9]])).degree == pytest.approx(0.5, abs=1e-12)  # EyesWeb: 1 / 3


def test_spike_sync_is_unchanged_when_the_trains_share_no_sample():
    result = SpikeSynchronization(window=60, hop=60)._process_window(spike_trains([10, 20, 30], [11, 21, 45]))
    assert result.degree == pytest.approx(4 / 6, abs=1e-12)


@pytest.mark.parametrize("sequence,events,expected", [("1 2 1", [1, 2, 1], 1), ("5", [5], 1), ("1 1", [1, 1, 0, 1, 1], 2)])
def test_sequence_detector_counts_a_call_that_completes_both_directions_once(sequence, events, expected):
    detector = SequenceDetector(sequence=sequence, any_order=True)
    for event in events:
        detector.process(event)
    assert detector.process(0).sequence_count == expected  # EyesWeb: 2, 2, 4


def test_temporal_synchronization_with_a_zero_threshold_is_finite():
    """rho = 0 for a threshold of 0 (EyesWeb: 1 - Q / 0 = inf, a NaN progression)."""
    block = TemporalSynchronization(number_of_inputs=2, thresholds=[0.0, 0.0], max_steps=100)
    result = block.process([-0.3, 0.2])
    assert result.state == 0 and result.progression == 0.5
    assert block.process([0.2, 0.1]).progression == 1.0
