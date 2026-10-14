import numpy as np
import pytest
from pyeyesweb.data_models.results import Status

# Import your features
from pyeyesweb.low_level import BoundingBoxFilledArea, SpectralArcLength, LogDimensionlessJerk, DirectionChange, Equilibrium, Symmetry


# ==========================================
# 1. STATIC FEATURES (Frame-by-Frame)
# ==========================================


def test_bounding_box_filled_area():
    feature = BoundingBoxFilledArea()

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

    result = feature.process(cube_points)

    assert result.ok
    assert hasattr(result, "contraction_index")
    assert np.isclose(result.contraction_index, 1.0)





def test_equilibrium():
    feature = Equilibrium()

    result = feature.process((-100, 0), (100, 0), (0, 0))

    assert result.ok
    assert hasattr(result, "value")
    assert hasattr(result, "angle")
    assert np.isclose(result.value, 1.0)





# ==========================================
# 2. DYNAMIC FEATURES (Time-Series)
# ==========================================


def test_direction_change_all_metrics():
    # Testing Strategy 2 API where both metrics are computed
    feature = DirectionChange(window=3, metrics=["cosine", "polygon"])

    for frame in ([0, 0], [1, 0], [1, 1]):
        result = feature.process(frame)
    assert result.ok
    assert result.cosine > 0.5
    assert result.polygon > 0.0

    flat = result.to_flat_dict("dir")
    assert "dir_cosine" in flat
    assert "dir_polygon" in flat


def test_direction_change_selective_metrics():
    # Only compute cosine
    feature = DirectionChange(window=3, metrics=["cosine"])

    for frame in ([0, 0], [1, 0], [2, 0]):
        result = feature.process(frame)
    assert result.ok
    assert np.isclose(result.cosine, 0.0)
    assert feature.outputs.names == ("cosine",)  # only what was requested is declared
    assert not hasattr(result, "polygon")

    flat = result.to_flat_dict("dir")
    assert "dir_cosine" in flat and "dir_polygon" not in flat

    feature.metrics = ["polygon"]  # the schema follows the parameter
    assert feature.outputs.names == ("polygon",)


def test_speed_profile_metric_api():
    feature = SpectralArcLength(window=50, sampling_rate=50.0)

    times = np.linspace(0, 1, 50)
    signal = np.sin(2 * np.pi * times)

    recording = feature.run(signal)
    result = feature._process_window(signal)
    assert recording.ok.sum() == 1 and recording.ok[-1]  # a result once the first window is full

    assert result.ok
    assert feature.outputs.names == ("spectral_arc_length",)  # one output per metric
    assert not np.isnan(result.spectral_arc_length)
    assert not hasattr(result, "log_dimensionless_jerk")

    flat = result.to_flat_dict("smooth")
    assert "smooth_spectral_arc_length" in flat


def test_log_dimensionless_jerk_input_mode_choice():
    signal = np.abs(np.sin(np.linspace(0, 3, 60))) * 40
    velocity = LogDimensionlessJerk(window=60)
    acceleration = LogDimensionlessJerk(window=60, input_mode="Acceleration")
    assert velocity.input_mode == "velocity" and acceleration.input_mode == "acceleration"
    assert velocity._process_window(signal).log_dimensionless_jerk != acceleration._process_window(signal).log_dimensionless_jerk
    with pytest.raises(ValueError, match="velocity"):
        LogDimensionlessJerk(input_mode="jerk")


def test_geometric_symmetry_unrolling():
    # Left=0, Right=1, Center=2
    feature = Symmetry(method="reflection", joint_pairs=[(0, 1)], center_of_symmetry=2)

    frame2 = np.array(
        [
            [-6, 3, 1],  # Left
            [6, 3, 1],  # Right
            [0, 3, 1],  # Center
        ]
    )

    result = feature.process(frame2)
    flat = result.to_flat_dict(prefix="sym")

    assert result.ok
    assert np.isclose(flat["sym_pair_symmetry_0_1"], 1.0)
    assert feature.outputs.flat_names == ("pair_symmetry_0_1",)
    assert result.pair_symmetry.shape == (1,)


# ==========================================
# 3. ARCHITECTURE & BEHAVIOR TESTS
# ==========================================


def test_frame_features_are_stateless():
    feature = Symmetry(method="reflection", joint_pairs=[(0, 1)])

    older, newest = np.array([[0, 0, 0], [1, 1, 1]]), np.array([[2, 0, 0], [-2, 0, 0]])
    first = feature.process(older).pair_symmetry
    result = feature.process(newest)

    assert result.ok
    assert not np.array_equal(result.pair_symmetry, first)
    assert np.array_equal(feature.process(older).pair_symmetry, first)  # the previous frame does not matter


def test_too_short_inputs_are_not_ok():
    assert Equilibrium().process((), (), ()).status == Status.INVALID_INPUT
    assert SpectralArcLength().process(1.0).status == Status.WARMING_UP


def test_bounding_box_filled_area_degenerate_hull_is_invalid_input():
    rng = np.random.default_rng(0)
    planar = np.c_[rng.random((6, 2)), np.zeros(6)]
    tilted = np.c_[rng.random(6), rng.random(6), np.zeros(6)] @ np.array([[1, 0, 0], [0, .6, .8], [0, -.8, .6]])
    for points, reason in ((rng.random((3, 3)), "fewer than 4 points"), (planar, "coplanar"), (tilted, "coplanar"),
                           (np.outer(rng.random(5), [1, 2, 3]), "coplanar")):
        result = BoundingBoxFilledArea().process(points)  # before: OK with index 0
        assert result.status == Status.INVALID_INPUT and reason in result.reason
        assert result.contraction_index == 0.0
    assert BoundingBoxFilledArea().process(rng.random((8, 3))).ok
