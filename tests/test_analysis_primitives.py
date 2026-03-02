import pytest
import numpy as np

from pyeyesweb.data_models.sliding_window import SlidingWindow
from pyeyesweb.analysis_primitives.clusterability import Clusterability
from pyeyesweb.analysis_primitives.rarity import Rarity
from pyeyesweb.analysis_primitives.statistical_moment import StatisticalMoment
from pyeyesweb.analysis_primitives.synchronization import Synchronization


# ==========================================
# ANALYSIS PRIMITIVES TESTS
# ==========================================

def test_clusterability():
    feature = Clusterability(n_neighbors=2)
    window = SlidingWindow(max_length=10, n_signals=1, n_dims=3)

    # Add 10 frames of 3D data (Random noise)
    for _ in range(10):
        window.append([np.random.rand(3)])

    result = feature(window)

    assert result.is_valid is True
    assert hasattr(result, 'clusterability')
    assert not np.isnan(result.clusterability)


def test_rarity():
    feature = Rarity(alpha=0.5)
    window = SlidingWindow(max_length=20, n_signals=1, n_dims=1)

    # Fill window with 19 identical values (highly probable)
    for _ in range(19):
        window.append([[5.0]])

    # Add 1 completely different value (highly rare)
    window.append([[100.0]])

    result = feature(window)

    assert result.is_valid is True
    assert result.rarity > 0.0  # Should flag as rare


def test_statistical_moment_unrolling():
    # Updated to use 'metrics' parameter to match new API
    feature = StatisticalMoment(methods=["mean", "std_dev"])
    # 1 signal, 2 dimensions (X, Y)
    window = SlidingWindow(max_length=5, n_signals=1, n_dims=2)

    data = np.array([
        [[1.0, 2.0]],
        [[3.0, 4.0]],
        [[5.0, 6.0]],
        [[7.0, 8.0]],
        [[9.0, 10.0]]
    ])

    for frame in data:
        window.append(frame)

    result = feature(window)
    flat = result.to_flat_dict(prefix="stat")

    assert result.is_valid is True
    # Mean of [1,3,5,7,9] is 5.0
    assert flat["stat_mean_0"] == 5.0
    # Mean of [2,4,6,8,10] is 6.0
    assert flat["stat_mean_1"] == 6.0

    assert "stat_std_dev_0" in flat
    assert "stat_std_dev_1" in flat


def test_statistical_moment_selective_metrics():
    """Verify that unrequested metrics are omitted from the flat dictionary."""
    feature = StatisticalMoment(methods=["mean"])
    window = SlidingWindow(max_length=5, n_signals=1, n_dims=2)

    for i in range(5):
        window.append([[float(i), float(i)]])

    result = feature(window)
    flat = result.to_flat_dict(prefix="stat")

    # The requested metric should be present
    assert "stat_mean_0" in flat
    # The unrequested metrics should be safely ignored and not clutter the dict
    assert "stat_std_dev_0" not in flat
    assert "stat_skewness_0" not in flat


def test_synchronization_api():
    feature = Synchronization()
    # 2 signals (e.g., left and right wrist speed), 1 dimension each
    window = SlidingWindow(max_length=50, n_signals=2, n_dims=1)

    t = np.linspace(0, 1, 50)
    # Generate two identical sine waves (perfectly in phase)
    s1 = np.sin(2 * np.pi * t)
    s2 = np.sin(2 * np.pi * t)

    for v1, v2 in zip(s1, s2):
        window.append([[v1], [v2]])

    result = feature(window)

    # We just ensure it doesn't crash and returns the correct contract
    # (Actual PLV math is tested in your signal_processing unit tests)
    assert hasattr(result, 'plv')