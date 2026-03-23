import pytest
import numpy as np
from pyeyesweb.data_models.sliding_window import SlidingWindow

# Import your features
from pyeyesweb.low_level import (
    BoundingBoxFilledArea,
    EllipsoidSphericity,
    PointsDensity,
    KineticEnergy,
    Smoothness,
    DirectionChange,
    Equilibrium,
    GeometricSymmetry,
)


# ==========================================
# 1. STATIC FEATURES (Frame-by-Frame)
# ==========================================


def test_bounding_box_filled_area():
    feature = BoundingBoxFilledArea()
    window = SlidingWindow(max_length=1, n_signals=8, n_dims=3)

    cube_points = np.array(
        [
            [0, 0, 0],
            [1, 0, 0],
            [1, 1, 0],
            [0, 1, 0],
            [0, 0, 1],
            [1, 0, 1],
            [1, 1, 1],
            [0, 1, 1],
        ]
    )
    window.append(cube_points)

    result = feature(window)

    assert result.is_valid is True
    assert hasattr(result, "contraction_index")
    assert np.isclose(result.contraction_index, 6.0)


def test_ellipsoid_sphericity():
    feature = EllipsoidSphericity()
    window = SlidingWindow(max_length=1, n_signals=6, n_dims=3)

    points = np.array(
        [[1, 0, 0], [-1, 0, 0], [0, 1, 0], [0, -1, 0], [0, 0, 1], [0, 0, -1]]
    )
    window.append(points)

    result = feature(window)

    assert result.is_valid is True
    assert np.isclose(result.sphericity, 1.0)


def test_points_density():
    feature = PointsDensity()
    window = SlidingWindow(max_length=1, n_signals=4, n_dims=3)

    points = np.array([[2, 0, 0], [-2, 0, 0], [0, 2, 0], [0, -2, 0]])
    window.append(points)

    result = feature(window)

    assert result.is_valid is True
    assert np.isclose(result.points_density, 2.0)


def test_equilibrium():
    feature = Equilibrium(left_foot_idx=0, right_foot_idx=1, barycenter_idx=2)
    window = SlidingWindow(max_length=1, n_signals=3, n_dims=3)

    frame = np.array([[-100, 0, 0], [100, 0, 0], [0, 0, 0]])
    window.append(frame)

    result = feature(window)

    assert result.is_valid is True
    assert hasattr(result, "value")
    assert hasattr(result, "angle")
    assert np.isclose(result.value, 1.0)


def test_kinetic_energy():
    feature = KineticEnergy(weights=2.0)
    window = SlidingWindow(max_length=1, n_signals=2, n_dims=3)

    velocities = np.array([[3, 0, 0], [3, 0, 0]])
    window.append(velocities)

    result = feature(window)

    assert result.is_valid is True
    assert np.isclose(result.total_energy, 18.0)
    assert np.allclose(result.component_energy, [18.0, 0.0, 0.0])


# ==========================================
# 2. DYNAMIC FEATURES (Time-Series)
# ==========================================


def test_direction_change_all_metrics():
    # Testing Strategy 2 API where both metrics are computed
    feature = DirectionChange(metrics=["cosine", "polygon"])

    turn_window = SlidingWindow(max_length=3, n_signals=1, n_dims=2)
    turn_window.append([[0, 0]])
    turn_window.append([[1, 0]])
    turn_window.append([[1, 1]])

    result = feature(turn_window)
    assert result.is_valid is True
    assert result.cosine > 0.5
    assert result.polygon > 0.0

    flat = result.to_flat_dict("dir")
    assert "dir_cosine" in flat
    assert "dir_polygon" in flat


def test_direction_change_selective_metrics():
    # Only compute cosine
    feature = DirectionChange(metrics=["cosine"])

    straight_window = SlidingWindow(max_length=3, n_signals=1, n_dims=2)
    straight_window.append([[0, 0]])
    straight_window.append([[1, 0]])
    straight_window.append([[2, 0]])

    result = feature(straight_window)
    assert result.is_valid is True
    assert np.isclose(result.cosine, 0.0)
    assert result.polygon is None  # Should be ignored

    flat = result.to_flat_dict("dir")
    assert "dir_cosine" in flat
    assert "dir_polygon" not in flat


def test_smoothness_api():
    # Defaults to computing both SPARC and Jerk
    feature = Smoothness(rate_hz=50.0)
    window = SlidingWindow(max_length=50, n_signals=1, n_dims=1)

    t = np.linspace(0, 1, 50)
    x = np.sin(2 * np.pi * t)

    for val in x:
        window.append([[val]])

    result = feature(window)

    assert result.is_valid is True
    assert hasattr(result, "sparc")
    assert hasattr(result, "jerk_rms")
    assert not np.isnan(result.sparc)


def test_smoothness_selective_metrics():
    # Test skipping Jerk computation
    feature = Smoothness(rate_hz=50.0, metrics=["sparc"])
    window = SlidingWindow(max_length=50, n_signals=1, n_dims=1)

    t = np.linspace(0, 1, 50)
    x = np.sin(2 * np.pi * t)
    for val in x:
        window.append([[val]])

    result = feature(window)

    assert result.is_valid is True
    assert result.sparc is not None
    assert result.jerk_rms is None

    flat = result.to_flat_dict("smooth")
    assert "smooth_sparc" in flat
    assert "smooth_jerk_rms" not in flat


def test_geometric_symmetry_unrolling():
    # Left=0, Right=1, Center=2
    feature = GeometricSymmetry(joint_pairs=[(0, 1)], center_of_symmetry=2)
    window = SlidingWindow(max_length=2, n_signals=3, n_dims=3)

    frame1 = np.array(
        [
            [-5, 2, 0],  # Left
            [5, 2, 0],  # Right
            [0, 2, 0],  # Center
        ]
    )
    frame2 = np.array(
        [
            [-6, 3, 1],  # Left
            [6, 3, 1],  # Right
            [0, 3, 1],  # Center
        ]
    )

    window.append(frame1)
    window.append(frame2)

    result = feature(window)
    flat = result.to_flat_dict(prefix="sym")

    assert result.is_valid is True
    assert np.isclose(flat["sym_pair_0_1"], 1.0)


# ==========================================
# 3. ARCHITECTURE & BEHAVIOR TESTS
# ==========================================


def test_static_feature_extracts_newest_frame():
    feature = PointsDensity()
    window = SlidingWindow(max_length=5, n_signals=2, n_dims=3)

    window.append(np.array([[0, 0, 0], [1, 1, 1]]))  # Older frame
    window.append(np.array([[2, 0, 0], [-2, 0, 0]]))  # Newest frame

    result = feature(window)

    assert result.is_valid is True
    assert np.isclose(result.points_density, 2.0)


def test_empty_window_safety():
    window = SlidingWindow(max_length=10, n_signals=3, n_dims=3)

    static_feature = Equilibrium()
    dynamic_feature = Smoothness()

    static_result = static_feature(window)
    dynamic_result = dynamic_feature(window)

    assert static_result.is_valid is False
    assert dynamic_result.is_valid is False


def test_kinetic_energy_flattening():
    feature = KineticEnergy(weights=2.0, labels=["LeftHand", "RightHand"])
    window = SlidingWindow(max_length=1, n_signals=2, n_dims=3)

    window.append(np.array([[4, 0, 0], [0, 3, 0]]))

    result = feature(window)
    flat_dict = result.to_flat_dict(prefix="ke")

    assert flat_dict["ke_total_energy"] == 25.0
    assert flat_dict["ke_energy_x"] == 16.0
    assert flat_dict["ke_energy_y"] == 9.0
    assert flat_dict["ke_energy_z"] == 0.0
    assert flat_dict["ke_joint_LeftHand_total"] == 16.0
    assert flat_dict["ke_joint_LeftHand_x"] == 16.0
    assert flat_dict["ke_joint_RightHand_y"] == 9.0
