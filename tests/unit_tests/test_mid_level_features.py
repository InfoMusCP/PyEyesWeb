import numpy as np

from pyeyesweb.data_models.results import Status
from pyeyesweb.low_level import DirectionChange
from pyeyesweb.mid_level import (
    Suddenness,
    SuddennessImpulsivity,
)


def _series(window_data):
    """A `(Time, N_signals, N_dims)` tensor as the `(N_signals * N_dims, Time)` series `_process_window` takes."""
    return np.asarray(window_data).reshape(len(window_data), -1).T


# ==========================================
# SUDDENNESS TESTS
# ==========================================


def test_suddenness_insufficient_frames():
    """Test that Suddenness gracefully fails if there are < 5 velocities (i.e. < 6 frames)."""
    feature = Suddenness(window=6, dims=3)
    # Shape: (Time=4, N_signals=1, N_dims=3)
    data = np.random.rand(4, 1, 3)

    result = feature._process_window(_series(data))

    assert result.status == Status.WARMING_UP


def test_suddenness_random_walk():
    """Test a valid, non-constant trajectory."""
    feature = Suddenness(window=20, dims=3)
    np.random.seed(42)
    data = np.random.rand(20, 1, 3)

    result = feature._process_window(_series(data))

    assert result.ok
    assert isinstance(result.alpha, float)
    assert isinstance(result.is_sudden, bool)


# ==========================================
# IMPULSIVITY TESTS
# ==========================================


def test_impulsivity_orchestration():
    """Test that SuddennessImpulsivity perfectly merges Suddenness and DirectionChange."""
    feature = SuddennessImpulsivity(window=30, dims=3, direction_change_epsilon=0.5)
    np.random.seed(42)
    # 30 frames, 1 joint, 3D
    data = np.random.rand(30, 1, 3)

    result = feature._process_window(_series(data))

    assert result.ok

    # Core mathematical contract: the index is direction change times the suddenness verdict, so 0 when not sudden
    cosine = DirectionChange(window=30, metrics=["cosine"])._process_window(data[:, 0, :].T).cosine
    sudden = Suddenness(window=30, dims=3)._process_window(_series(data)).is_sudden
    assert result.impulsivity_index == cosine * float(sudden)
    assert tuple(result.schema.names) == ("impulsivity_index",)


def test_impulsivity_streaming_api():
    """Frames streamed through `process` give the result of the window."""
    feature = SuddennessImpulsivity(window=10, dims=3, direction_change_epsilon=0.5)
    np.random.seed(42)
    frames = np.random.rand(10, 1, 3)

    results = [feature.process(point) for point in frames[:, 0, :]]

    assert all(result.status == Status.WARMING_UP for result in results[:-1])
    assert results[-1].ok
    assert isinstance(results[-1].impulsivity_index, float)
    assert results[-1].impulsivity_index == feature._process_window(_series(frames)).impulsivity_index
