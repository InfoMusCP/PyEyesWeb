"""Known-answer (analytic) checks: inputs whose result follows from the definition, or whose ordering is certain."""

import math

import numpy as np
import pytest

pytest.importorskip("pyeyesweb._core")

from pyeyesweb.analysis_primitives import Rarity  # noqa: E402
from pyeyesweb.data_models.results import Status  # noqa: E402
from pyeyesweb.low_level import (  # noqa: E402
    BoundingBoxFilledArea, EllipsoidSphericity, Harmonicity, LogDimensionlessJerk, SpectralArcLength,
    SubmovementCount, Symmetry)
from pyeyesweb.mid_level import ContractionImpulsivity, Suddenness  # noqa: E402

FS = 50.0


def _prism(width, depth, height, angle):
    """Corners of a `width` x `depth` x `height` box turned by `angle` about z."""
    c, s = math.cos(angle), math.sin(angle)
    return np.array([[x * c - y * s, x * s + y * c, z] for x in (0, width) for y in (0, depth) for z in (0, height)])


@pytest.mark.parametrize("angle", [0.0, math.pi / 6, math.pi / 4])
def test_bounding_box_filled_area_of_a_turned_box(angle):
    a, b, h = 2.0, 1.0, 1.0
    # the hull is the box itself; the axis-aligned box around it is wider by the turn
    w, d = a * math.cos(angle) + b * math.sin(angle), a * math.sin(angle) + b * math.cos(angle)
    expected = (a * b + a * h + b * h) / (w * d + w * h + d * h)
    result = BoundingBoxFilledArea().process(_prism(a, b, h, angle))
    assert result.ok
    assert result.contraction_index == pytest.approx(expected)


def _bell(n=100):
    return np.sin(np.linspace(0, np.pi, n)) ** 2


def _jerky(n=100):
    return _bell(n) * (1 + 0.5 * np.sin(np.linspace(0, 12 * np.pi, n)))


def _last(feature, series):
    return feature.run(series)[-1]


def test_spectral_arc_length_smooth_beats_jerky_and_ignores_scale():
    sal = lambda v: _last(SpectralArcLength(window=len(v), sampling_rate=FS), v).spectral_arc_length  # noqa: E731
    assert sal(_jerky()) < sal(_bell()) < 0
    assert sal(3 * _bell()) == pytest.approx(sal(_bell()))  # the spectrum is normalised by its maximum


def test_spectral_arc_length_of_a_constant_speed_is_invalid():
    result = _last(SpectralArcLength(window=20, sampling_rate=FS), np.full(20, 2.0))
    assert result.status == Status.INVALID_INPUT


def test_log_dimensionless_jerk_of_a_quadratic_speed():
    n = 50
    speed = (np.arange(n) / FS) ** 2  # constant jerk 2, duration n / fs, peak ((n - 1) / fs) ** 2
    expected = -math.log(4 * (n / (n - 1)) ** 4)
    result = _last(LogDimensionlessJerk(window=n, sampling_rate=FS), speed)
    assert result.log_dimensionless_jerk == pytest.approx(expected)


def test_log_dimensionless_jerk_smooth_beats_jerky():
    ldj = lambda v: _last(LogDimensionlessJerk(window=len(v), sampling_rate=FS), v).log_dimensionless_jerk  # noqa: E731
    assert ldj(_jerky()) < ldj(_bell())


def test_harmonicity_of_one_bell_is_one():
    assert _last(Harmonicity(window=100, sampling_rate=FS), _bell()).harmonicity == 1.0


def test_harmonicity_counts_peaks_against_gradient_sign_changes():
    # 1 + cos(4 pi t): maxima at both ends and in the middle, minima between; the gradient changes sign at the 3 turning
    # points (2 minima, 1 inner maximum) and only the inner maximum is a peak: 2 * 1 / 3
    speed = 1 + np.cos(4 * np.pi * np.linspace(0, 1, 103))
    assert _last(Harmonicity(window=103, sampling_rate=FS), speed).harmonicity == pytest.approx(2 / 3)


@pytest.mark.parametrize("centres", [[], [0.5], [0.25, 0.75], [0.2, 0.5, 0.8]])
def test_submovement_count_of_separated_gaussians(centres):
    t = np.linspace(0, 1, 200)
    speed = sum((np.exp(-(((t - c) / 0.04) ** 2)) for c in centres), np.zeros_like(t))
    assert _last(SubmovementCount(window=200, sampling_rate=FS), speed).submovement_count == len(centres)


def _mode_distance(stream, window):
    return _last(Rarity(method="mode_distance", window=window, alpha=1.0), stream).rarity


def test_rarity_of_a_constant_signal_is_zero():
    assert _mode_distance(np.full(30, 4.0), 16) == 0


def test_rarity_of_a_single_outlier():
    # window 16 -> 4 bins; 15 zeros in bin 0 and the newest value 1 in bin 3: |0 - 3| * (15/16 - 1/16) * alpha
    assert _mode_distance(np.r_[np.zeros(15), 1.0], 16) == pytest.approx(3 * 14 / 16)
    # the outlier is still in the window but the newest sample is in the mode bin: not rare
    assert _mode_distance(np.r_[np.zeros(14), 1.0, 0.0], 16) == 0


def _suddenness(speeds, method):
    positions = np.c_[np.r_[0, np.cumsum(speeds)], np.zeros(len(speeds) + 1)]
    return _last(Suddenness(window=len(positions), method=method), positions)


def test_suddenness_of_a_constant_speed_is_the_gaussian_default():
    result = _suddenness(np.full(40, 1.5), "constrained")
    assert (result.alpha, result.beta, result.gamma) == (2, 0, 0)


@pytest.mark.parametrize("method", ["constrained", "quantile"])
def test_suddenness_percentile_statistics_of_linear_speeds(method):
    # 101 sorted speeds 3000 + (k - 50)^3 / 100 (all positive) are symmetric about x50 (beta 0); x25, x75 = 3000 -+ 156.25, so
    # gamma = (x75 - x25) / (x75 - x50) = 2, and (x95 - x5) / (x75 - x25) = 5.8 is inside the range the fit accepts
    result = _suddenness(3000 + (np.arange(101) - 50.0) ** 3 / 100, method)
    assert result.beta == pytest.approx(0, abs=1e-12)
    assert result.gamma == pytest.approx(2)


def test_symmetry_reflection_of_a_mirrored_and_a_shifted_pair():
    labels = ["left", "right", "centre"]
    mirrored = np.array([[-1, 2, 3], [1, 2, 3], [0, 0, 0]], dtype=float)
    symmetry = Symmetry(method="reflection", labels=labels, pairs=[("left", "right")], reference_point="centre")
    assert symmetry.process(mirrored).pair_symmetry[0] == pytest.approx(1)
    shifted = mirrored.copy()
    shifted[1, 0] = 2  # reflected right is (-2, 2, 3): error 1, normalised by |left| + |right|
    expected = 1 - 1 / (math.sqrt(14) + math.sqrt(17))
    assert symmetry.process(shifted).pair_symmetry[0] == pytest.approx(expected, abs=1e-6)


def _axis_points(a, b, c):
    return np.array([[a, 0, 0], [-a, 0, 0], [0, b, 0], [0, -b, 0], [0, 0, c], [0, 0, -c]], dtype=float)


def test_ellipsoid_sphericity_of_a_sphere():
    result = EllipsoidSphericity().process(_axis_points(2, 2, 2))
    assert result.sphericity == pytest.approx(1)
    assert result.axis_ratio == pytest.approx(1)
    assert EllipsoidSphericity().process_axes(3, 3, 3).sphericity == pytest.approx(1)


def test_ellipsoid_sphericity_of_an_ellipsoid():
    # points on the axes: the covariance is diagonal with the squared semi-axes, so the radii keep the ratio 3 : 2 : 1
    result = EllipsoidSphericity().process(_axis_points(3, 2, 1))
    radii = np.asarray(result.radii)
    assert radii / radii[0] == pytest.approx([1, 2 / 3, 1 / 3])
    assert result.axis_ratio == pytest.approx(1 / 3)
    assert 0 < result.sphericity < 1


# One gesture: three frames of motion (QoM above 0.01), the contraction index rising 0.3 -> 0.6, closed by a still frame.
QOM = [0.0, 0.5, 0.5, 0.0]
CONTRACTION = [0.2, 0.3, 0.6, 0.6]
GESTURE = dict(peak_threshold=0.4, gesture_duration=10)


def test_contraction_impulsivity_per_frame_without_a_rate():
    result = ContractionImpulsivity(**GESTURE).run(QOM, CONTRACTION)[-1]
    assert result.impulsivity_index == pytest.approx(0.3 / 3)  # change 0.3 over 3 frames
    assert result.gesture_duration == 3


@pytest.mark.parametrize("rate", [25.0, 100.0])
def test_contraction_impulsivity_per_second_follows_the_rate(rate):
    result = ContractionImpulsivity(sampling_rate=rate, **GESTURE).run(QOM, CONTRACTION)[-1]
    assert result.impulsivity_index == pytest.approx(0.3 / (3 / rate))


def test_contraction_impulsivity_timestamps_do_not_replace_the_rate():
    # timestamps only feed the time rule: the index is set by `sampling_rate`, the same with or without them
    stamps = np.arange(4) / 25.0
    timed = ContractionImpulsivity(sampling_rate=25.0, **GESTURE).run(QOM, CONTRACTION, timestamps=stamps)[-1]
    assert timed.impulsivity_index == pytest.approx(0.3 / (3 / 25.0))
    assert ContractionImpulsivity(**GESTURE).run(QOM, CONTRACTION, timestamps=stamps)[-1].impulsivity_index == pytest.approx(0.1)


def test_contraction_impulsivity_units():
    units = lambda **p: {o.name: o.unit for o in ContractionImpulsivity(**p).outputs}  # noqa: E731
    assert units(sampling_rate=25.0) == {"impulsivity_index": "1/s", "gesture_duration": "frames"}
    assert units()["impulsivity_index"] == "1/frame"
