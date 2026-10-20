"""Regression tests for smoothness metrics against the reference definitions
(Balasubramanian et al. 2012/2015, Melendez-Calderon et al. 2021,
Richman & Moorman 2000)."""
import numpy as np

from pyeyesweb.low_level.smoothness import Smoothness
from pyeyesweb.utils.math_utils import (
    compute_sparc,
    compute_ldlj,
    compute_jerk_rms,
    compute_sample_entropy,
    compute_harmonicity_index,
)

FS = 100.0


def _min_jerk_speed(duration=1.0):
    t = np.arange(0, duration, 1 / FS)
    tau = t / duration
    return 30 * tau ** 2 * (1 - tau) ** 2 / duration


def _submovements(k, step):
    s1 = _min_jerk_speed()
    s = np.zeros(step * (k - 1) + len(s1))
    for i in range(k):
        s[step * i:step * i + len(s1)] += s1
    return np.concatenate([np.zeros(30), s, np.zeros(30)])


def test_sparc_minimum_jerk_reference_value():
    # Reference implementation gives -1.4059 for this profile
    assert np.isclose(compute_sparc(_submovements(1, 50), FS), -1.4059, atol=1e-3)


def test_sparc_decreases_with_fragmentation():
    values = [compute_sparc(_submovements(k, 90), FS) for k in (1, 2, 3)]
    assert values[0] > values[1] > values[2]


def test_ldlj_v_reference_formula():
    v = _submovements(1, 50)
    dt = 1 / FS
    T = len(v) * dt
    jerk = np.diff(v, 2) / dt ** 2
    expected = -np.log(T ** 3 / np.max(v) ** 2 * np.sum(jerk ** 2) * dt)
    assert np.isclose(compute_ldlj(v, FS, 'velocity'), expected)


def test_ldlj_a_is_invariant_to_constant_offset():
    acc = np.gradient(np.c_[_min_jerk_speed(), np.zeros(100), np.zeros(100)], 1 / FS, axis=0)
    a = compute_ldlj(acc, FS, 'acceleration')
    b = compute_ldlj(acc + np.array([0, 0, 9810.0]), FS, 'acceleration')
    assert np.isclose(a, b)


def test_ldlj_degenerate_returns_nan():
    assert np.isnan(compute_ldlj(np.zeros(50), FS, 'velocity'))


def test_jerk_rms_uses_velocity_vector():
    # Circular motion at constant speed: speed has no jerk, the vector does
    t = np.arange(0, 2, 1 / FS)
    vel = np.c_[-np.sin(2 * np.pi * t), np.cos(2 * np.pi * t)]
    assert compute_jerk_rms(np.linalg.norm(vel, axis=1), FS) < 1e-6
    assert np.isclose(compute_jerk_rms(vel, FS), (2 * np.pi) ** 2, rtol=0.05)


def test_sample_entropy_matches_brute_force():
    x = np.random.default_rng(0).standard_normal(120)
    m, r = 2, 0.2 * np.std(x)
    A = B = 0
    for i in range(len(x) - m):
        for j in range(i + 1, len(x) - m):
            if np.max(np.abs(x[i:i + m] - x[j:j + m])) <= r:
                B += 1
                if abs(x[i + m] - x[j + m]) <= r:
                    A += 1
    assert np.isclose(compute_sample_entropy(x), -np.log(A / B))


def test_harmonicity_detects_hidden_submovement():
    assert np.isclose(compute_harmonicity_index(_submovements(1, 50), FS), 1.0)
    # Two overlapping submovements merged into one peak with a "shoulder"
    assert compute_harmonicity_index(_submovements(2, 50), FS) < 1.0


def test_smoothness_accepts_velocity_vectors():
    speed = _submovements(2, 90)
    vel = np.c_[speed, np.zeros_like(speed), np.zeros_like(speed)]
    feature = Smoothness(rate_hz=FS)
    r_speed = feature.compute(speed[:, None, None])
    r_vec = feature.compute(vel[:, None, :])
    assert r_vec.is_valid
    assert np.isclose(r_speed.ldlj_v, r_vec.ldlj_v)
    assert np.isclose(r_speed.sparc, r_vec.sparc, atol=1e-2)


def test_smoothness_filter_with_16_or_fewer_samples():
    feature = Smoothness(rate_hz=FS)
    for n in (15, 16):
        assert feature.compute(1 + np.abs(np.sin(np.linspace(0, 3, n)))).is_valid
