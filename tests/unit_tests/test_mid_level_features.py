import pytest
import numpy as np

from pyeyesweb.data_models.sliding_window import SlidingWindow
from pyeyesweb.mid_level.suddenness import Suddenness, SuddennessResult
from pyeyesweb.mid_level.impulsivity import Impulsivity, ImpulsivityResult
from pyeyesweb.mid_level.lightness import Lightness, LightnessResult


# ==========================================
# SUDDENNESS TESTS
# ==========================================

def test_suddenness_insufficient_frames():
    """Test that Suddenness gracefully fails if there are < 5 velocities (i.e. < 6 frames)."""
    feature = Suddenness(algo="new")
    # Shape: (Time=4, N_signals=1, N_dims=3)
    data = np.random.rand(4, 1, 3)

    result = feature.compute(data)

    assert isinstance(result, SuddennessResult)
    assert result.is_valid is False


def test_suddenness_zero_velocity():
    """Test fallback mechanism when the subject is completely still."""
    feature = Suddenness(algo="new")
    # 10 frames of exactly the same position (0 velocity)
    data = np.ones((10, 1, 3)) * 5.0
    print(data)
    result = feature.compute(data)
    print(result)
    assert result.is_valid is True
    # When velocity is constant, it falls back to Gaussian default (alpha=2.0)
    assert result.alpha == 2.0
    assert result.beta == 0.0
    assert result.is_sudden is False


def test_suddenness_random_walk():
    """Test a valid, non-constant trajectory."""
    feature = Suddenness(algo="new")
    np.random.seed(42)
    data = np.random.rand(20, 1, 3)

    result = feature.compute(data)

    assert result.is_valid is True
    assert isinstance(result.alpha, float)
    assert isinstance(result.is_sudden, bool)


# ==========================================
# IMPULSIVITY TESTS
# ==========================================

def test_impulsivity_orchestration():
    """Test that Impulsivity perfectly merges Suddenness and DirectionChange via pure math API."""
    feature = Impulsivity(direction_change_epsilon=0.5)
    np.random.seed(42)
    # 30 frames, 1 joint, 3D
    data = np.random.rand(30, 1, 3)

    result = feature.compute(data)

    assert isinstance(result, ImpulsivityResult)
    assert result.is_valid is True

    # Core mathematical contract: Impulsivity MUST be 0 if it is not sudden
    if not result.is_sudden:
        assert result.impulsivity_index == 0.0
    else:
        assert result.impulsivity_index == result.direction_change_val * float(result.is_sudden)


def test_impulsivity_streaming_api():
    """Test the __call__ method using a SlidingWindow."""
    feature = Impulsivity(direction_change_epsilon=0.5)
    window = SlidingWindow(max_length=10, n_signals=1, n_dims=3)
    np.random.seed(42)

    for _ in range(10):
        window.append([np.random.rand(3)])

    result = feature(window)

    assert result.is_valid is True
    assert isinstance(result.impulsivity_index, float)


# ==========================================
# LIGHTNESS TESTS
# ==========================================

def test_lightness_insufficient_data():
    """Lightness needs at least 2 frames of velocity."""
    feature = Lightness(alpha=0.5)
    data = np.random.rand(1, 1, 3)

    result = feature.compute(data)

    assert isinstance(result, LightnessResult)
    assert result.is_valid is False


def test_lightness_zero_energy_handling():
    """Test that Lightness handles zero kinetic energy without divide-by-zero errors."""
    feature = Lightness(alpha=0.5)
    # Velocities are exactly zero
    data = np.zeros((10, 1, 3))

    result = feature.compute(data)

    assert result.is_valid is True
    # If total_energy == 0, the weight is forced to 0.0, so the inverted weight is 1.0.
    # Constant inverted weights of 1.0 means rarity = 0.0
    assert result.lightness == 0.0
    assert result.latest_weight_index == 0.0


def test_lightness_valid_kinematics():
    """Test standard behavior with moving velocities."""
    feature = Lightness(alpha=0.5)
    np.random.seed(42)
    # Shape: (Time=20, N_signals=2 (e.g. 2 hands), N_dims=3)
    data = np.random.rand(20, 2, 3)

    result = feature.compute(data)

    assert result.is_valid is True
    assert 0.0 <= result.latest_weight_index <= 1.0
    assert isinstance(result.lightness, float)