import numpy as np

from pyeyesweb.data_models.results import Status
from pyeyesweb.analysis_primitives import Rarity


# ==========================================
# ANALYSIS PRIMITIVES TESTS
# ==========================================


def test_rarity():
    feature = Rarity(method="mode_distance", window=20, alpha=0.5)

    # Fill window with 19 identical values (highly probable)
    for _ in range(19):
        feature.process(5.0)

    # Add 1 completely different value (highly rare)
    result = feature.process(100.0)

    assert result.ok
    assert result.rarity > 0.0  # Should flag as rare


def test_synchronization_api():
    from pyeyesweb.analysis_primitives.synchronization import PhaseLockingValue
    feature = PhaseLockingValue(window=50)
    times = np.linspace(0, 1, 50)
    s1 = np.sin(2 * np.pi * times)  # two identical sine waves (perfectly in phase)

    results = feature.run(s1, s1)

    # We just ensure it doesn't crash and returns the correct contract
    # (Actual PLV math is tested in your signal_processing unit tests)
    assert results.status[-1] == Status.OK and results.status[0] == Status.WARMING_UP
    assert "phase_locking_value" in results.schema.names




def test_rarity_mode_distance_non_finite_window_is_invalid_input():
    for bad in (np.nan, np.inf):
        feature = Rarity(method="mode_distance", window=8)
        for value in (1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0):
            feature.process(value)
        result = feature.process(bad)  # before: the core raised ValueError("autodetected range is not finite")
        assert result.status == Status.INVALID_INPUT and result.reason == "NaN or infinite values"
        assert np.isnan(result.rarity)


def test_rarity_constant_stream_is_ok_and_zero():
    # a constant window is not degenerate: the newest value is the mode, nothing is atypical
    feature = Rarity(method="mode_distance", window=8)
    for _ in range(8):
        result = feature.process(3.0)
    assert result.ok and result.rarity == 0.0
